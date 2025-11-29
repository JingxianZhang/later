from fastapi import APIRouter, HTTPException
from .models import IngestRequest, IngestResponse, ChatRequest, ChatResponse, Citation, ToolInfo
from .canonical import canonicalize_url
from .embeddings import embed_texts
from .config import settings
from .db import db
from typing import List
import json
from .flow import run_ingest_flow
from fastapi import Query
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from .flow import resolve_tool as node_resolve_tool, ingest as node_ingest, augment_sources as node_augment_sources, research as node_research, juror as node_juror, dbwrite as node_dbwrite
from pydantic import BaseModel
from fastapi import status, Query
from fastapi import UploadFile, File, Form
from fastapi import Request
from .validators import is_plausible_product_name, fallback_name_from_ocr
import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(payload: IngestRequest, request: Request) -> IngestResponse:
    if not payload.url and not payload.name:
        raise HTTPException(status_code=400, detail="Provide either url or name")
    user_id = request.headers.get("x-user-id")
    result = await run_ingest_flow(str(payload.url) if payload.url else None, payload.name, bool(payload.force), user_id)
    return IngestResponse(tool_id=str(result["tool_id"]), status=str(result["status"]))


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    # Embed the question and retrieve top-k similar chunks directly (no RPC)
    question_vec = (await embed_texts([payload.question]))[0]
    qvec_str = "[" + ",".join(str(x) for x in question_vec) + "]"
    # Determine scope and caps
    scope = getattr(payload, "scope", "tool") or "tool"
    prefer_one_pager = bool(getattr(payload, "prefer_one_pager", False))
    # Default K is smaller when we prefer the one_pager; can be overridden by rag_limit
    default_k = 4 if prefer_one_pager else 8
    try:
        requested_k = int(getattr(payload, "rag_limit")) if getattr(payload, "rag_limit") is not None else default_k
    except Exception:
        requested_k = default_k
    # Clamp to sane bounds
    k = max(0, min(12, requested_k))

    # Fetch one_pager as additional structured context (only when tool scope and tool_id present)
    op_ctx = ""
    if scope == "tool" and payload.tool_id:
        tool = await db.fetchrow("SELECT one_pager FROM tools WHERE id = $1::uuid", payload.tool_id)
        if tool and tool["one_pager"]:
            try:
                op = tool["one_pager"] if isinstance(tool["one_pager"], dict) else json.loads(str(tool["one_pager"]))
                overview = op.get("overview") or ""
                features = op.get("features") or []
                pricing = op.get("pricing") or {}
                tech = op.get("tech_stack") or []
                op_ctx = "\n".join(filter(None, [
                    f"Overview: {overview}" if overview else "",
                    f"Features: {', '.join(features[:8])}" if features else "",
                    f"Pricing: {json.dumps(pricing)}" if pricing else "",
                    f"Tech: {', '.join(tech[:8])}" if tech else "",
                ]))
            except Exception:
                op_ctx = ""

    # Retrieve relevant chunks according to scope
    if scope == "global":
        rows = await db.fetch(
            """
            SELECT source_url, chunk_text
            FROM documents
            WHERE chunk_embedding IS NOT NULL
            ORDER BY chunk_embedding <#> $1::vector
            LIMIT 48
            """,
            qvec_str,
        )
    else:
        # Default to tool scope
        rows = await db.fetch(
            """
            SELECT source_url, chunk_text
            FROM documents
            WHERE tool_id = $1::uuid AND chunk_embedding IS NOT NULL
            ORDER BY chunk_embedding <#> $2::vector
            LIMIT 48
            """,
            payload.tool_id,
            qvec_str,
        )
    # Build snippets and citations; include only top-k in context
    snippets: List[str] = [r["chunk_text"][:500] for r in rows][:k]
    citations: List[Citation] = [Citation(source_url=r["source_url"], snippet=r["chunk_text"][:160]) for r in rows][: max(2, min(8, k if k > 0 else 2))]

    # Simple answer via OpenAI with provided snippets
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    context_blocks = []
    if op_ctx:
        context_blocks.append(f"Structured facts:\n{op_ctx}")
    if snippets:
        context_blocks.append("Retrieved snippets:\n" + "\n".join(f"- {s}" for s in snippets))
    context = "\n\n".join(context_blocks) if context_blocks else "No additional context."
    prompt = (
        "Answer the user question concisely using the provided context. "
        "Prefer structured facts when available. Cite sources by number [1], [2] where relevant.\n\n"
        f"{context}\n\nQuestion: {payload.question}"
    )
    completion = await client.chat.completions.create(
        model=settings.model_primary,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    answer = completion.choices[0].message.content or ""
    # Return at least two citations if available
    return ChatResponse(answer=answer, citations=citations[: max(2, min(8, len(citations)))])


@router.get("/tools/{tool_id}", response_model=ToolInfo)
async def get_tool(tool_id: str, request: Request) -> ToolInfo:
    tool = await db.fetchrow("SELECT id, name, status, canonical_url, one_pager FROM tools WHERE id = $1::uuid", tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    docs = await db.fetchrow("SELECT COUNT(*) AS c FROM documents WHERE tool_id = $1::uuid", tool_id)
    updates = await db.fetchrow("SELECT COUNT(*) AS c FROM tool_updates WHERE tool_id = $1::uuid", tool_id)
    src_rows = await db.fetch("SELECT DISTINCT source_url FROM documents WHERE tool_id = $1::uuid AND source_url <> '' LIMIT 8", tool_id)
    # Determine which version to serve:
    # If a user is provided, return the one_pager/media for the version linked to that user.
    # Otherwise, fall back to the latest version.
    user_id = request.headers.get("x-user-id")
    ver = None
    if user_id:
        ver = await db.fetchrow(
            """
            SELECT tv.id
            FROM user_tool_versions uv
            JOIN tool_versions tv ON uv.tool_version_id = tv.id
            WHERE uv.user_id = $1::uuid AND tv.tool_id = $2::uuid
            ORDER BY uv.linked_at DESC NULLS LAST, tv.version_no DESC
            LIMIT 1
            """,
            user_id,
            tool_id,
        )
    if not ver:
        ver = await db.fetchrow("SELECT id FROM tool_versions WHERE tool_id = $1::uuid AND is_latest = TRUE", tool_id)
    media_rows = []
    if ver:
        media_rows = await db.fetch(
            """
            SELECT platform, url, title, author, author_handle, is_influencer, metrics, published_at, thumbnail_url
            FROM media_items
            WHERE tool_version_id = $1::uuid
            ORDER BY published_at DESC NULLS LAST, created_at DESC
            LIMIT 6
            """,
            ver["id"],
        )
    # Choose one_pager from user-linked version if available; otherwise use tool.one_pager
    raw_one_pager = tool["one_pager"]
    if ver:
        row_op = await db.fetchrow("SELECT one_pager FROM tool_versions WHERE id = $1::uuid", ver["id"])
        if row_op and row_op["one_pager"]:
            raw_one_pager = row_op["one_pager"]
    parsed_one_pager: dict = {}
    if raw_one_pager:
        if isinstance(raw_one_pager, dict):
            parsed_one_pager = raw_one_pager
        else:
            try:
                parsed_one_pager = json.loads(str(raw_one_pager))
            except Exception:
                parsed_one_pager = {}
    return ToolInfo(
        id=str(tool["id"]),
        name=tool["name"],
        canonical_url=tool["canonical_url"],
        status=tool["status"],
        one_pager=parsed_one_pager,
        documents=int(docs["c"]),
        updates=int(updates["c"]),
        sources=[r["source_url"] for r in src_rows],
        media_items=[
            {
                "platform": m["platform"],
                "url": m["url"],
                "title": m["title"] or "",
                "author": m["author"] or "",
                "author_handle": m["author_handle"] or "",
                "is_influencer": bool(m["is_influencer"]),
                "metrics": m["metrics"] or {},
                "published_at": m["published_at"].isoformat() if m["published_at"] else None,
                "thumbnail_url": m["thumbnail_url"] or "",
            }
            for m in media_rows
        ],
    )


@router.get("/tools")
async def list_tools(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)) -> list[dict]:
    user_id = request.headers.get("x-user-id")
    # If user scoped, compute watchlist per user and overview/last_updated from user's linked version if exists
    if user_id:
        try:
            rows = await db.fetch(
                """
                SELECT
                  t.id,
                  t.name,
                  t.status,
                  EXISTS(SELECT 1 FROM user_watchlist uw WHERE uw.tool_id = t.id AND uw.user_id = $3::uuid) AS watchlist,
                  t.canonical_url,
                  COALESCE((SELECT tv.one_pager->>'overview' FROM user_tool_versions uv
                            JOIN tool_versions tv ON uv.tool_version_id = tv.id
                            WHERE uv.user_id = $3::uuid AND tv.tool_id = t.id
                            ORDER BY uv.linked_at DESC NULLS LAST, tv.version_no DESC
                            LIMIT 1), t.one_pager->>'overview') AS overview,
                  COALESCE((SELECT tv.one_pager->>'last_updated' FROM user_tool_versions uv
                            JOIN tool_versions tv ON uv.tool_version_id = tv.id
                            WHERE uv.user_id = $3::uuid AND tv.tool_id = t.id
                            ORDER BY uv.linked_at DESC NULLS LAST, tv.version_no DESC
                            LIMIT 1), t.one_pager->>'last_updated') AS last_updated,
                  (SELECT COUNT(*) FROM tool_updates u WHERE u.tool_id = t.id) AS updates
                FROM tools t
                ORDER BY t.id DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
                user_id,
            )
        except Exception as e:
            # Fallback if user_watchlist table not yet migrated
            rows = await db.fetch(
                """
                SELECT
                  t.id,
                  t.name,
                  t.status,
                  t.watchlist,
                  t.canonical_url,
                  COALESCE(t.one_pager->>'overview','') AS overview,
                  COALESCE(t.one_pager->>'last_updated','') AS last_updated,
                  (SELECT COUNT(*) FROM tool_updates u WHERE u.tool_id = t.id) AS updates
                FROM tools t
                ORDER BY t.id DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
    else:
        rows = await db.fetch(
            """
            SELECT
              t.id,
              t.name,
              t.status,
              FALSE AS watchlist,
              t.canonical_url,
              COALESCE(t.one_pager->>'overview','') AS overview,
              COALESCE(t.one_pager->>'last_updated','') AS last_updated,
              (SELECT COUNT(*) FROM tool_updates u WHERE u.tool_id = t.id) AS updates
            FROM tools t
            ORDER BY t.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "status": r["status"],
            "watchlist": bool(r["watchlist"]),
            "canonical_url": r["canonical_url"] or "",
            "overview": r["overview"] or "",
            "last_updated": r["last_updated"] or "",
            "updates": int(r["updates"]),
        }
        for r in rows
    ]


def _sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get("/ingest/stream")
async def ingest_stream(url: Optional[str] = None, name: Optional[str] = None, force: bool = Query(False), user_id: Optional[str] = None) -> StreamingResponse:
    if not url and not name:
        raise HTTPException(status_code=400, detail="Provide either url or name")

    async def gen() -> AsyncGenerator[bytes, None]:
        state: Dict[str, Any] = {"url": url, "name": name, "force": force, "user_id": user_id}

        had_error = False

        async def run_node(label: str, fn):
            nonlocal had_error
            await asyncio.sleep(0)
            yield _sse_event("progress", {"node": label, "status": "start"})
            try:
                update = await fn(state)  # type: ignore[misc]
                if update:
                    state.update(update)
                yield _sse_event("progress", {"node": label, "status": "finish", "state": {k: state.get(k) for k in ["tool_id", "status", "canonical_url"] if k in state}})
            except Exception as e:
                yield _sse_event("error", {"node": label, "message": str(e)})
                had_error = True
                return

        for label, fn in [
            ("resolve_tool", node_resolve_tool),
            ("ingest", node_ingest),
            ("augment_sources", node_augment_sources),
            ("research", node_research),
            ("juror", node_juror),
            ("dbwrite", node_dbwrite),
        ]:
            async for ev in run_node(label, fn):
                yield ev.encode()
            if had_error:
                break

        yield _sse_event("done", {"tool_id": state.get("tool_id"), "status": state.get("status", "pending_research")}).encode()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/ingest/image", response_model=IngestResponse)
async def ingest_image(request: Request, file: UploadFile = File(...), hint: str | None = Form(default=None)) -> IngestResponse:
    """
    Accept an image (screenshot), OCR it, extract a primary product name, and run the ingest flow
    with OCR text included so research can leverage it.
    """
    data = await file.read()
    try:
        logger.info("[api.ingest_image] file_len=%d content_type=%s", len(data or b""), file.content_type)
    except Exception:
        pass
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    mime = file.content_type or "image/png"
    from .vision import ocr_image_to_text
    from .research import extract_primary_product_name
    from .flow import run_ingest_flow_with_ocr

    ocr_text = await ocr_image_to_text(data, mime)
    if not ocr_text:
        raise HTTPException(status_code=400, detail="Failed to extract text from image")
    product_name = await extract_primary_product_name(ocr_text, hint)
    try:
        logger.info("[api.ingest_image] ocr_len=%d extracted_name='%s' plausible=%s", len(ocr_text or ""), (product_name or "")[:120], is_plausible_product_name(product_name or ""))
    except Exception:
        pass
    if not product_name or not is_plausible_product_name(product_name):
        # Try a simple fallback from OCR first line/title
        fb = fallback_name_from_ocr(ocr_text)
        try:
            logger.info("[api.ingest_image] fallback_name='%s' plausible=%s", fb, is_plausible_product_name(fb))
        except Exception:
            pass
        if not fb or not is_plausible_product_name(fb):
            raise HTTPException(status_code=400, detail="Could not infer a valid product name from this screenshot")
        product_name = fb
    user_id = request.headers.get("x-user-id")
    result = await run_ingest_flow_with_ocr(product_name, ocr_text, source_label="screenshot", user_id=user_id)
    return IngestResponse(tool_id=str(result["tool_id"]), status=str(result["status"]))

class LinkStartResponse(BaseModel):
    token: str
    expires_at: str

class LinkStatusResponse(BaseModel):
    linked: bool

@router.post("/auth/link/telegram/start", response_model=LinkStartResponse)
async def link_telegram_start(request: Request) -> LinkStartResponse:
    """
    Generate a short-lived token for the current user to link Telegram via /start <TOKEN>.
    """
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id")
    import secrets
    from datetime import datetime, timezone, timedelta
    token = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    await db.execute(
        "INSERT INTO user_link_tokens (token, user_id, expires_at, used) VALUES ($1, $2::uuid, $3, FALSE)",
        token,
        user_id,
        expires_at,
    )
    return LinkStartResponse(token=token, expires_at=expires_at.isoformat())


@router.get("/auth/link/telegram/status", response_model=LinkStatusResponse)
async def link_telegram_status(request: Request) -> LinkStatusResponse:
    """
    Check if the current user is already linked to a Telegram chat_id.
    """
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id")
    row = await db.fetchrow("SELECT chat_id FROM telegram_users WHERE linked_user_id = $1::uuid", user_id)
    return LinkStatusResponse(linked=bool(row))


class WatchlistRequest(BaseModel):
    watch: bool


@router.post("/tools/{tool_id}/watchlist")
async def update_watchlist(tool_id: str, payload: WatchlistRequest, request: Request) -> dict:
    """
    Per-user watchlist toggle. Requires X-User-Id header.
    """
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-Id")
    if bool(payload.watch):
        # Add to user_watchlist (idempotent via PK)
        try:
            await db.execute(
                "INSERT INTO user_watchlist (user_id, tool_id) VALUES ($1::uuid, $2::uuid) ON CONFLICT DO NOTHING",
                user_id,
                tool_id,
            )
        except Exception as e:
            # Fallback if migration not yet applied: update legacy global flag
            await db.execute(
                "UPDATE tools SET watchlist = TRUE WHERE id = $1::uuid",
                tool_id,
            )
    else:
        try:
            await db.execute(
                "DELETE FROM user_watchlist WHERE user_id = $1::uuid AND tool_id = $2::uuid",
                user_id,
                tool_id,
            )
        except Exception:
            # Fallback: clear legacy global flag
            await db.execute(
                "UPDATE tools SET watchlist = FALSE WHERE id = $1::uuid",
                tool_id,
            )
    return {"ok": True, "tool_id": tool_id, "watchlist": bool(payload.watch)}


class RefreshResponse(BaseModel):
    processed: int
    linked_users: int
    skipped_recent: int


@router.post("/tools/{tool_id}/refresh", response_model=RefreshResponse)
async def refresh_single_tool(tool_id: str) -> RefreshResponse:
    """
    Refresh a single tool and link all watching users to the newly created version.
    """
    tool = await db.fetchrow("SELECT id, canonical_url, name FROM tools WHERE id = $1::uuid", tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    # Run ingest flow (force False; freshness gate will skip if too recent)
    from .flow import run_ingest_flow
    canonical_url = tool["canonical_url"]
    name = tool["name"]
    await run_ingest_flow(canonical_url, name, False, None)
    # Find latest version
    latest = await db.fetchrow("SELECT id FROM tool_versions WHERE tool_id = $1::uuid AND is_latest = TRUE", tool_id)
    if not latest:
        return RefreshResponse(processed=0, linked_users=0, skipped_recent=0)
    version_id = str(latest["id"])
    # Link all watchers to latest
    watchers = await db.fetch("SELECT user_id FROM user_watchlist WHERE tool_id = $1::uuid", tool_id)
    linked = 0
    for w in watchers:
        try:
            await db.execute(
                "INSERT INTO user_tool_versions (user_id, tool_version_id) VALUES ($1::uuid, $2::uuid)",
                w["user_id"],
                version_id,
            )
            linked += 1
        except Exception:
            # ignore duplicates
            continue
    return RefreshResponse(processed=1, linked_users=linked, skipped_recent=0)


@router.post("/watchlist/refresh", response_model=RefreshResponse)
async def refresh_watchlist(limit: int = Query(100, ge=1, le=1000)) -> RefreshResponse:
    """
    Refresh all tools that have at least one watcher and link all watchers to the newest version.
    """
    tools = await db.fetch(
        """
        SELECT DISTINCT t.id, t.canonical_url, t.name
        FROM tools t
        JOIN user_watchlist uw ON uw.tool_id = t.id
        ORDER BY t.id DESC
        LIMIT $1
        """,
        limit,
    )
    from .flow import run_ingest_flow
    processed = 0
    skipped_recent = 0  # not tracked precisely; freshness gate is internal
    linked_total = 0
    for t in tools:
        try:
            await run_ingest_flow(t["canonical_url"], t["name"], False, None)
            latest = await db.fetchrow("SELECT id FROM tool_versions WHERE tool_id = $1::uuid AND is_latest = TRUE", t["id"])
            if not latest:
                continue
            version_id = str(latest["id"])
            watchers = await db.fetch("SELECT user_id FROM user_watchlist WHERE tool_id = $1::uuid", t["id"])
            for w in watchers:
                try:
                    await db.execute(
                        "INSERT INTO user_tool_versions (user_id, tool_version_id) VALUES ($1::uuid, $2::uuid)",
                        w["user_id"],
                        version_id,
                    )
                    linked_total += 1
                except Exception:
                    continue
            processed += 1
        except Exception:
            continue
    return RefreshResponse(processed=processed, linked_users=linked_total, skipped_recent=skipped_recent)


@router.delete("/tools/{tool_id}/versions/latest")
async def delete_latest_tool_version(tool_id: str, user_id: str | None = Query(default=None)) -> dict:
    """
    Delete semantics:
    - If user_id is provided:
        - If other users still reference this tool (via user_tool_versions), only unlink this user
          from all versions of the tool and do NOT delete any versions or the tool.
        - If no other users reference this tool, delete the entire tool (cascades).
    - If user_id is not provided:
        - Delete the latest tool_version and cascade related version-scoped data.
          Promote the next highest version to latest and sync tools.one_pager; or clear if none.
    """
    # Acquire a connection to perform a small transactional sequence
    if db.pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not connected")
    conn = await db.pool.acquire()
    try:
        async with conn.transaction():
            if user_id:
                # Count distinct other users referencing this tool
                other_users = await conn.fetchrow(
                    """
                    SELECT COUNT(DISTINCT uv.user_id) AS c
                    FROM user_tool_versions uv
                    JOIN tool_versions tv ON uv.tool_version_id = tv.id
                    WHERE tv.tool_id = $1::uuid AND (uv.user_id IS DISTINCT FROM $2::uuid)
                    """,
                    tool_id,
                    user_id,
                )
                other_count = int(other_users["c"]) if other_users else 0
                if other_count > 0:
                    # Unlink this user from all versions of this tool; keep shared data intact
                    await conn.execute(
                        """
                        DELETE FROM user_tool_versions
                        WHERE user_id = $1::uuid
                          AND tool_version_id IN (SELECT id FROM tool_versions WHERE tool_id = $2::uuid)
                        """,
                        user_id,
                        tool_id,
                    )
                    return {"ok": True, "unlinked_only": True, "tool_id": tool_id}
                # No other users reference this tool; safe to delete entire tool (cascades)
                await conn.execute("DELETE FROM tools WHERE id = $1::uuid", tool_id)
                return {"ok": True, "tool_deleted": True, "tool_id": tool_id}

            latest = await conn.fetchrow(
                "SELECT id, version_no FROM tool_versions WHERE tool_id = $1::uuid AND is_latest = TRUE",
                tool_id,
            )
            if not latest:
                raise HTTPException(status_code=404, detail="No latest version found for tool")
            latest_id = latest["id"]
            # Delete the latest version; cascades will remove related rows
            await conn.execute("DELETE FROM tool_versions WHERE id = $1::uuid", latest_id)
            # Pick new latest (highest version_no) if exists
            new_latest = await conn.fetchrow(
                "SELECT id, one_pager FROM tool_versions WHERE tool_id = $1::uuid ORDER BY version_no DESC LIMIT 1",
                tool_id,
            )
            new_latest_id: str | None = None
            if new_latest:
                new_latest_id = str(new_latest["id"])
                await conn.execute("UPDATE tool_versions SET is_latest = TRUE WHERE id = $1::uuid", new_latest["id"])
                await conn.execute(
                    "UPDATE tools SET one_pager = $1 WHERE id = $2::uuid",
                    new_latest["one_pager"],
                    tool_id,
                )
            else:
                # No versions remain; clear the tool-level one_pager
                await conn.execute("UPDATE tools SET one_pager = '{}'::jsonb WHERE id = $1::uuid", tool_id)
        return {"ok": True, "deleted_version_id": str(latest_id), "new_latest_version_id": new_latest_id}
    finally:
        await db.pool.release(conn)
