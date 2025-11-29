from typing import TypedDict, Any, Optional, List
from langgraph.graph import StateGraph, END
from .canonical import canonicalize_url
from .scrape import fetch_clean_text
from .link_classify import fetch_text_for_url, classify_link
from .chunk import recursive_character_split
from .embeddings import embed_texts
from .research import synthesize_one_pager, pick_five_claims, resolve_official_site_via_llm, classify_screenshot_intent
from .juror import verify_claims
from .db import db
import json
from langsmith import traceable
from tavily import TavilyClient
from .config import settings
import re
from datetime import datetime, timezone, timedelta
from .validators import is_plausible_product_name


class FlowState(TypedDict, total=False):
    url: Optional[str]
    name: Optional[str]
    force: bool
    user_id: Optional[str]
    canonical_url: Optional[str]
    source_url: Optional[str]
    tool_id: Optional[str]
    status: str
    ocr_text: Optional[str]
    clean_text: str
    chunks: List[str]
    embeddings: List[List[float]]
    one_pager: dict[str, Any]
    verdicts: list[tuple[str, bool, str]]
    augmented_urls: List[str]
    augmented_media: List[dict]
    skip_processing: bool


@traceable(name="resolve_tool")
async def resolve_tool(state: FlowState) -> FlowState:
    url = state.get("url")
    name = state.get("name")
    force = bool(state.get("force"))
    canonical = canonicalize_url(url) if url else None

    tool_id: Optional[str] = None
    status = "pending_research"
    url_official: Optional[str] = None

    # If name only, attempt to discover official site using both search + LLM arbiter
    if not canonical and name:
        candidates_for_llm: list[str] = []
        candidate_urls: list[str] = []
        # Gather candidates via Tavily, if available
        if settings.tavily_api_key:
            try:
                client = TavilyClient(api_key=settings.tavily_api_key.get_secret_value())  # type: ignore[arg-type]
                queries = [
                    f"{name} official site",
                    f"{name} homepage",
                    f"{name} product website",
                    f"{name} company website",
                    f"{name} website",
                    f"site:wikipedia.org {name}",
                ]
                seen_c = set()
                for q in queries:
                    res = client.search(query=q, max_results=8)
                    for item in res.get("results", []):
                        title = item.get("title") or ""
                        u = item.get("url") or ""
                        snippet = (item.get("content") or "")[:160]
                        if not u:
                            continue
                        if u in seen_c:
                            continue
                        seen_c.add(u)
                        # Pass title + url + snippet to LLM to aid notability choice
                        candidates_for_llm.append(f"{title} — {u} — {snippet}")
                        candidate_urls.append(u)
            except Exception:
                candidates_for_llm = []
                candidate_urls = []
        # Ask LLM to pick the single official homepage
        llm_pick = ""
        try:
            llm_pick = await resolve_official_site_via_llm(name, candidates_for_llm)
        except Exception:
            llm_pick = ""
        SOCIAL_HOSTS = ("x.com", "twitter.com", "linkedin.com", "youtube.com", "youtu.be", "tiktok.com")
        def is_social(u: str) -> bool:
            try:
                from urllib.parse import urlparse
                h = (urlparse(u).hostname or "").lower()
                return any(h.endswith(s) or s in h for s in SOCIAL_HOSTS)
            except Exception:
                return False
        if llm_pick and not is_social(llm_pick):
            canonical = canonicalize_url(llm_pick)
        else:
            # Heuristic fallback: first non-social apex-like domain from candidates
            for u in candidate_urls:
                if not u or is_social(u):
                    continue
                cand = canonicalize_url(u)
                if cand:
                    canonical = cand
                    break

    if canonical:
        existing = await db.fetchrow("SELECT id, status FROM tools WHERE canonical_url = $1", canonical)
        if existing:
            tool_id = str(existing["id"])
            status = existing["status"]
            # If a recent version exists within 6 hours and not forced, skip heavy processing
            try:
                ver = await db.fetchrow(
                    "SELECT created_at FROM tool_versions WHERE tool_id = $1::uuid AND is_latest = TRUE",
                    tool_id,
                )
                if ver:
                    created_at = ver["created_at"]
                    if isinstance(created_at, datetime):
                        now = datetime.now(timezone.utc)
                        if (now - created_at) < timedelta(hours=6) and not force:
                            return {
                                "canonical_url": canonical,
                                "original_url": url,
                                "url_official": canonical,
                                "tool_id": tool_id,
                                "status": status,
                                "skip_processing": True,
                            }
            except Exception:
                pass
            if force:
                await db.execute("DELETE FROM documents WHERE tool_id = $1::uuid AND source_url = $2", tool_id, url or "")
        url_official = canonical or url_official
    # Try alias if not found
    if not tool_id:
        key = (canonical or "").lower() or (name or "").lower()
        if key:
            alias = await db.fetchrow("SELECT tool_id FROM tool_aliases WHERE LOWER(alias_value) = $1", key)
            if alias:
                tool_id = str(alias["tool_id"])
    if not tool_id:
        # Validate name before creating new tool to avoid junk records
        if not canonical and not (name and is_plausible_product_name(name)):
            raise ValueError("Invalid product name; cannot create tool")
        # Create new
        row = await db.fetchrow(
            """
            INSERT INTO tools (name, canonical_url, one_pager, embedding, category_tags, watchlist, status)
            VALUES ($1, $2, '{}'::jsonb, NULL, ARRAY[]::text[], FALSE, 'pending_research')
            RETURNING id
            """,
            name or (canonical or "unknown"),
            canonical,
        )
        tool_id = str(row["id"])
        # Seed aliases
        aliases: list[tuple[str, str, float]] = []
        try:
            if name:
                aliases.append((name.lower(), "name", 0.9))
            if canonical:
                from urllib.parse import urlparse
                host = (urlparse(canonical).hostname or "").lower()
                if host:
                    aliases.append((host, "domain", 0.95))
        except Exception:
            pass
        if aliases:
            await db.executemany(
                "INSERT INTO tool_aliases (tool_id, alias_value, alias_type, confidence) VALUES ($1::uuid, $2, $3, $4)",
                [(tool_id, a, t, c) for (a, t, c) in aliases],
            )

    return {
        "canonical_url": canonical,
        "original_url": url,
        "url_official": url_official or canonical,
        "tool_id": tool_id,
        "status": status,
    }


@traceable(name="ingest")
async def ingest(state: FlowState) -> FlowState:
    if state.get("skip_processing"):
        # Return a benign update to satisfy LangGraph invariants
        return {"status": state.get("status", "pending_research")}
    url = state.get("url") or state.get("url_official") or state.get("canonical_url")
    tool_id = state["tool_id"]
    name = state.get("name") or ""
    ocr_text = state.get("ocr_text") or ""

    print(f"[flow.ingest] start tool_id={tool_id} url={url} name={name}")
    # Validate URL scheme; if invalid (e.g., garbage from mis-parsing), ignore and fall back to OCR/name
    def is_valid_http(u: str) -> bool:
        try:
            from urllib.parse import urlparse
            p = urlparse(u)
            return bool(p.scheme in ("http", "https") and p.netloc)
        except Exception:
            return False
    use_url = url if (url and is_valid_http(str(url))) else None
    if use_url:
        base_text = await fetch_text_for_url(url)
        # Prefer OCR text as leading context if provided (e.g., screenshots of docs/pricing)
        clean_text = (ocr_text + "\n\n" + base_text) if ocr_text else base_text
    else:
        # No URL — rely on OCR text when available, otherwise fall back to the provided name
        clean_text = ocr_text or name
    chunks = recursive_character_split(clean_text)
    embeddings = await embed_texts(chunks) if chunks else []
    print(f"[flow.ingest] done chunks={len(chunks)} embeds={len(embeddings)}")

    args: list[tuple] = []
    for idx, (text, vec) in enumerate(zip(chunks, embeddings)):
        vec_str = "[" + ",".join(str(x) for x in vec) + "]"
        # Preserve a non-empty source_url for provenance; fallback to provided source label for screenshots
        src = str(url or state.get("source_url") or "")
        args.append((tool_id, src, idx, text, vec_str))
    if args:
        await db.executemany(
            "INSERT INTO documents (tool_id, source_url, chunk_index, chunk_text, chunk_embedding) VALUES ($1::uuid, $2, $3, $4, $5::vector)",
            args,
        )

    return {"clean_text": clean_text, "chunks": chunks, "embeddings": embeddings}


@traceable(name="research")
async def research(state: FlowState) -> FlowState:
    if state.get("skip_processing"):
        # Return a benign update to satisfy LangGraph invariants
        return {"status": state.get("status", "pending_research")}
    clean_text = state.get("clean_text") or ""
    ocr_text = state.get("ocr_text") or ""
    tool_id = state.get("tool_id") or ""
    name = state.get("name") or ""
    # Aggregate additional context from already-indexed documents to improve coverage:
    # prioritize pricing/features/competitors/news signals, then backfill with recent/general chunks.
    keywords_priority = [
        "pricing", "price", "$", "cost", "plan", "tier",
        "feature", "capability", "benefit",
        "alternative", "competitor", "vs ", "compare",
        "update", "release", "announcement", "news", "roadmap"
    ]
    rows = await db.fetch(
        """
        SELECT source_url, chunk_text
        FROM documents
        WHERE tool_id = $1::uuid
        ORDER BY id DESC
        LIMIT 400
        """,
        tool_id,
    )
    prioritized: list[str] = []
    secondary: list[str] = []
    pricing_snippets: list[str] = []
    for r in rows:
        txt = (r["chunk_text"] or "")[:800]
        low = txt.lower()
        if any(k in low for k in keywords_priority):
            prioritized.append(txt)
        else:
            secondary.append(txt)
        if any(k in low for k in ["pricing", "price", "plan", "tier", "$"]):
            pricing_snippets.append(txt)
    bundle_parts: list[str] = []
    if clean_text:
        bundle_parts.append(clean_text[:4000])
    # Take more from prioritized first, then secondary, up to ~12k chars
    acc = 0
    for src in prioritized + secondary:
        if acc >= 12000:
            break
        bundle_parts.append(src)
        acc += len(src)
    combined_text = "\n\n".join(bundle_parts) if bundle_parts else clean_text
    # If OCR present, classify intent to guide synthesis
    screenshot_intent = None
    try:
        if ocr_text:
            screenshot_intent = await classify_screenshot_intent(ocr_text)
    except Exception:
        screenshot_intent = None
    one_pager = await synthesize_one_pager(combined_text, ocr_text=ocr_text or None, screenshot_intent=screenshot_intent)
    # Normalize/sort recent updates by date descending for UI
    try:
        from .research import normalize_and_sort_recent_updates
        one_pager = normalize_and_sort_recent_updates(one_pager)
    except Exception:
        pass
    # If pricing still empty, run targeted pricing extraction
    if not one_pager.get("pricing"):
        from .research import resolve_pricing_via_llm
        pricing = await resolve_pricing_via_llm(name, pricing_snippets[:20])
        if pricing:
            one_pager["pricing"] = pricing
    return {"one_pager": one_pager}


@traceable(name="juror")
async def juror(state: FlowState) -> FlowState:
    if state.get("skip_processing"):
        # Return a benign update to satisfy LangGraph invariants
        return {"status": state.get("status", "pending_research")}
    one_pager = state.get("one_pager") or {}
    claims = await pick_five_claims(one_pager)
    verdicts = await verify_claims(claims)
    return {"verdicts": verdicts}


@traceable(name="dbwrite")
async def dbwrite(state: FlowState) -> FlowState:
    if state.get("skip_processing"):
        # Return a benign update to satisfy LangGraph invariants
        return {"status": state.get("status", "partially_verified")}
    tool_id = state["tool_id"]
    one_pager = state.get("one_pager") or {}
    verdicts = state.get("verdicts") or []
    augmented_urls = state.get("augmented_urls") or []
    augmented_media = state.get("augmented_media") or []
    # Optionally refine tool name if synthesis produced a better product_name
    new_name = str((one_pager.get("product_name") or "")).strip()
    try:
        if new_name:
            from .validators import is_plausible_product_name
            # Fetch current name
            cur = await db.fetchrow("SELECT name FROM tools WHERE id = $1::uuid", tool_id)
            cur_name = str(cur["name"] or "") if cur else ""
            # If current name looks implausible or is a raw URL, update to the synthesized product name
            if (not is_plausible_product_name(cur_name)) or cur_name.startswith("http"):
                await db.execute("UPDATE tools SET name = $1 WHERE id = $2::uuid", new_name, tool_id)
    except Exception:
        pass

    await db.execute(
        "UPDATE tools SET one_pager = $1::jsonb, status = 'partially_verified' WHERE id = $2::uuid",
        json.dumps(one_pager),
        tool_id,
    )
    for claim, ok, url in verdicts:
        await db.execute(
            """
            INSERT INTO tool_updates (tool_id, field_changed, new_value, citation_source, source_agent)
            VALUES ($1::uuid, $2, $3, $4, 'juror')
            """,
            tool_id,
            "claim",
            claim if ok else f"UNVERIFIED: {claim}",
            url,
        )

    # Create new tool_version and mark it latest
    # Find previous latest
    prev = await db.fetchrow("SELECT id, version_no FROM tool_versions WHERE tool_id = $1::uuid AND is_latest = TRUE", tool_id)
    prev_id = prev["id"] if prev else None
    next_no = (prev["version_no"] + 1) if prev else 1
    if prev_id:
        await db.execute("UPDATE tool_versions SET is_latest = FALSE WHERE id = $1::uuid", prev_id)
    version_row = await db.fetchrow(
        """
        INSERT INTO tool_versions (tool_id, version_no, is_latest, base_version_id, one_pager, diff_from_prev)
        VALUES ($1::uuid, $2, TRUE, $3::uuid, $4::jsonb, '{}'::jsonb)
        RETURNING id
        """,
        tool_id,
        next_no,
        prev_id,
        json.dumps(one_pager),
    )
    version_id = str(version_row["id"])
    # Link to user if provided
    user_id = state.get("user_id")
    if user_id:
        try:
            await db.execute(
                "INSERT INTO user_tool_versions (user_id, tool_version_id) VALUES ($1::uuid, $2::uuid)",
                user_id,
                version_id,
            )
        except Exception:
            pass
    # Snapshot documents informing version (limit to recent ones)
    doc_ids = await db.fetch("SELECT id FROM documents WHERE tool_id = $1::uuid ORDER BY last_crawled DESC NULLS LAST, id DESC LIMIT 200", tool_id)
    if doc_ids:
        await db.executemany(
            "INSERT INTO tool_version_documents (tool_version_id, document_id) VALUES ($1::uuid, $2::uuid) ON CONFLICT DO NOTHING",
            [(version_id, str(r["id"])) for r in doc_ids],
        )
    # Store media_items from augmented_media (enriched)
    def platform_for(url: str) -> str:
        try:
            from urllib.parse import urlparse
            host = (urlparse(url).hostname or "").lower()
            if "youtube." in host or "youtu." in host:
                return "youtube"
            if "tiktok." in host:
                return "tiktok"
            if host.endswith("x.com") or "twitter." in host:
                return "x"
            if "linkedin." in host:
                return "linkedin"
            return "other"
        except Exception:
            return "other"
    if augmented_media:
        # Prefer version-scoped media_items schema; fall back to tool-scoped if not available
        try:
            await db.executemany(
                """
                INSERT INTO media_items (tool_version_id, platform, url, title, author, author_handle, is_influencer, metrics, published_at, thumbnail_url)
                VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb, NULL, $9)
                ON CONFLICT DO NOTHING
                """,
                [
                    (
                        version_id,
                        (m.get("platform") or platform_for(m.get("url",""))),
                        m.get("url",""),
                        (m.get("title") or "")[:255],
                        (m.get("author") or "")[:255],
                        (m.get("author_handle") or "")[:255],
                        bool(m.get("is_influencer") or False),
                        json.dumps(m.get("metrics") or {}),
                        m.get("thumbnail_url") or "",
                    )
                    for m in augmented_media
                ],
            )
        except Exception:
            # Fallback: tool-scoped media_items schema
            await db.executemany(
                """
                INSERT INTO media_items (tool_id, platform, url, title, author, author_handle, is_influencer, metrics, published_at, thumbnail_url, score)
                VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb, NULL, $9, 0)
                ON CONFLICT DO NOTHING
                """,
                [
                    (
                        tool_id,
                        (m.get("platform") or platform_for(m.get("url",""))),
                        m.get("url",""),
                        (m.get("title") or "")[:255],
                        (m.get("author") or "")[:255],
                        (m.get("author_handle") or "")[:255],
                        bool(m.get("is_influencer") or False),
                        json.dumps(m.get("metrics") or {}),
                        m.get("thumbnail_url") or "",
                    )
                    for m in augmented_media
                ],
            )

    return {"status": "partially_verified"}


builder = StateGraph(FlowState)
builder.add_node("resolve_tool", resolve_tool)
builder.add_node("ingest", ingest)

@traceable(name="augment_sources")
async def augment_sources(state: FlowState) -> FlowState:
    if state.get("skip_processing"):
        return {"augmented_urls": [], "augmented_media": []}
    url = state.get("url") or state.get("url_official") or state.get("canonical_url") or ""
    name = state.get("name") or ""
    tool_id = state["tool_id"]

    if not settings.tavily_api_key:
        # Explicitly record that no augmentation occurred
        return {"augmented_urls": []}

    client = TavilyClient(api_key=settings.tavily_api_key.get_secret_value())  # type: ignore[arg-type]
    queries = []
    if name:
        queries.append(f"{name} official documentation")
        queries.append(f"{name} product blog")
        queries.append(f"{name} news")
        queries.append(f"{name} pricing")
        queries.append(f"{name} competitors")
        queries.append(f"{name} alternatives")
        # social/video targets
        queries.append(f'site:youtube.com "{name}" review OR demo')
        queries.append(f'site:x.com "{name}"')
        queries.append(f'site:twitter.com "{name}"')
        queries.append(f'site:linkedin.com "{name}"')
    if url:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        base = host.split(":")[0]
        queries.append(f"site:{base} documentation")
        queries.append(f"{base} blog")
        queries.append(f"site:{base} pricing")

    seen = set([url])
    augmented: List[str] = []
    augmented_media: List[dict] = []
    highlights_added = 0
    docs_indexed = 0
    MAX_HIGHLIGHTS = 6
    MAX_DOCS = 12
    def platform_from_url(u: str) -> str:
        if "youtube.com" in u or "youtu.be" in u: return "youtube"
        if "tiktok.com" in u: return "tiktok"
        if "x.com" in u or "twitter.com" in u: return "x"
        if "linkedin.com" in u: return "linkedin"
        return "other"
    influencers = {"elonmusk","sama","jensenh","satyanadella","sundarpichai"}
    def score_item(title: str, u: str, meta: dict) -> float:
        s = 0.0
        if any(h in u for h in ["youtube.com","tiktok.com","x.com","linkedin.com"]): s += 0.5
        if any(h in u for h in influencers): s += 2.0
        views = 0
        m = re.search(r"([0-9][0-9,\\.]+)\\s*(views|likes)", (meta.get("content","") or "")[:200].lower())
        if m:
            try:
                views = int(m.group(1).replace(",","").replace(".",""))
            except Exception:
                views = 0
        s += min(views / 100000.0, 3.0)
        return s
    def youtube_thumbnail(u: str) -> str:
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(u)
            if "youtu.be" in (parsed.hostname or ""):
                vid = (parsed.path or "/").strip("/").split("/")[0]
            else:
                vid = parse_qs(parsed.query).get("v", [""])[0]
            return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg" if vid else ""
        except Exception:
            return ""
    def author_from_url(u: str) -> str:
        try:
            from urllib.parse import urlparse
            p = urlparse(u)
            parts = (p.path or "/").strip("/").split("/")
            return parts[0] if parts else ""
        except Exception:
            return ""
    for q in queries:
        if highlights_added >= MAX_HIGHLIGHTS and docs_indexed >= MAX_DOCS:
            break
        try:
            res = client.search(query=q, max_results=5)
            for item in res.get("results", []):
                u = item.get("url")
                if not u or u in seen:
                    continue
                p = platform_from_url(u)
                title = item.get("title") or ""
                meta = {"content": item.get("content") or ""}
                s = score_item(title, u, meta)
                # For Highlights: allow lower threshold and ensure at least two social items via fallback
                if p in {"youtube","tiktok","x","linkedin"} and highlights_added < MAX_HIGHLIGHTS and (s >= 0.5 or (p in {"x","linkedin"} and highlights_added < 2) or (p == "youtube" and s >= 1.0)):
                    # keep URL to add as media at dbwrite time; also index content for RAG
                    seen.add(u)
                    augmented.append(u)
                    thumb = youtube_thumbnail(u) if p == "youtube" else ""
                    augmented_media.append({
                        "platform": p,
                        "url": u,
                        "title": title[:255],
                        "author": "",
                        "author_handle": author_from_url(u),
                        "is_influencer": any(h in u for h in influencers),
                        "metrics": {},
                        "published_at": None,
                        "thumbnail_url": thumb,
                        "score": s,
                    })
                    highlights_added += 1
                # For non-social docs, index content but do not add to augmented list (to keep Highlights social-focused)
                # fetch, chunk, embed, insert (limit chunks per source)
                # Skip support/help/community pages to avoid noise
                if any(seg in (u or "").lower() for seg in ["support.", "/support", "/help", "community."]):
                    continue
                if docs_indexed >= MAX_DOCS:
                    continue
                clean = await fetch_clean_text(u)
                chunks = recursive_character_split(clean)
                if not chunks:
                    continue
                chunks = chunks[:6]
                embeds = await embed_texts(chunks)
                args: list[tuple] = []
                for idx, (text, vec) in enumerate(zip(chunks, embeds)):
                    vec_str = "[" + ",".join(str(x) for x in vec) + "]"
                    args.append((tool_id, u, idx, text, vec_str))
                await db.executemany(
                    "INSERT INTO documents (tool_id, source_url, chunk_index, chunk_text, chunk_embedding) VALUES ($1::uuid, $2, $3, $4, $5::vector)",
                    args,
                )
                seen.add(u)
                docs_indexed += 1
                if highlights_added >= MAX_HIGHLIGHTS and docs_indexed >= MAX_DOCS:
                    break
        except Exception:
            continue
    # Return augmented URLs for traceability
    return {"augmented_urls": augmented, "augmented_media": augmented_media}
builder.add_node("research", research)
builder.add_node("juror", juror)
builder.add_node("dbwrite", dbwrite)
builder.add_node("augment_sources", augment_sources)
builder.set_entry_point("resolve_tool")
builder.add_edge("resolve_tool", "ingest")
builder.add_edge("ingest", "augment_sources")
builder.add_edge("augment_sources", "research")
builder.add_edge("research", "juror")
builder.add_edge("juror", "dbwrite")
builder.add_edge("dbwrite", END)
graph = builder.compile()


@traceable(name="run_ingest_flow")
async def run_ingest_flow(url: Optional[str], name: Optional[str], force: bool, user_id: Optional[str] = None) -> dict[str, Any]:
    state: FlowState = {"url": url, "name": name, "force": force, "user_id": user_id}
    result = await graph.ainvoke(state)
    return {"tool_id": result.get("tool_id"), "status": result.get("status", "pending_research")}


@traceable(name="run_ingest_flow_with_ocr")
async def run_ingest_flow_with_ocr(name: str, ocr_text: str, source_label: str = "screenshot", force: bool = False, user_id: Optional[str] = None) -> dict[str, Any]:
    """
    Variant entrypoint used when OCR text is available (e.g., from screenshots).
    Passes OCR text into the flow and tags provenance via source_label.
    """
    state: FlowState = {"url": None, "name": name, "force": force, "ocr_text": ocr_text, "source_url": source_label, "user_id": user_id}
    result = await graph.ainvoke(state)
    return {"tool_id": result.get("tool_id"), "status": result.get("status", "pending_research")}

