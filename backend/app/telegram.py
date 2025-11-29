from fastapi import APIRouter, HTTPException, Path
from typing import Any, Optional
from .config import settings
import asyncio
import httpx
from .flow import run_ingest_flow, run_ingest_flow_with_ocr
from .canonical import canonicalize_url
from .vision import ocr_image_to_text
from .research import extract_primary_product_name
from .db import db
from .validators import is_plausible_product_name
import logging
import html

logger = logging.getLogger(__name__)

def _web_link_for_tool(tool_id: str) -> str:
    base = settings.web_base_url or (settings.allowed_origins[0] if settings.allowed_origins else "")
    try:
        if base and not base.endswith("/"):
            base = base + "/"
        if base:
            return f"{base}?tool={tool_id}"
    except Exception:
        pass
    # No web base configured; return empty so callers can decide how to message
    return ""

router = APIRouter()


def _extract_text_and_url(message: dict[str, Any]) -> tuple[str, Optional[str]]:
    """
    Return (raw_text, url_if_any)
    """
    text = str(message.get("text") or message.get("caption") or "").strip()
    url: Optional[str] = None
    # Prefer Telegram entities for accuracy
    entities = message.get("entities") or message.get("caption_entities") or []
    if isinstance(entities, list) and text:
        for ent in entities:
            try:
                if ent.get("type") == "url":
                    offset = int(ent.get("offset", 0))
                    length = int(ent.get("length", 0))
                    url = text[offset : offset + length]
                    break
            except Exception:
                continue
    # Fallback simple heuristic
    if not url and text.startswith("http"):
        url = text.split()[0]
    return text, url


async def _send_message(chat_id: int, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: bool = False) -> None:
    if not settings.telegram_bot_token:
        return
    token = settings.telegram_bot_token.get_secret_value()
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if disable_web_page_preview:
                payload["disable_web_page_preview"] = True
            await client.post(api, json=payload)
        except Exception:
            return


@router.post("/telegram/webhook/{token}")
async def telegram_webhook(update: dict[str, Any], token: str = Path(...)) -> dict[str, str]:
    # Verify secret path token
    if not settings.telegram_webhook_secret or token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": "no_message"}
    chat = message.get("chat") or {}
    chat_id = int(chat.get("id", 0))
    if chat_id == 0:
        return {"ok": "no_chat"}

    # Ignore bot commands like /start and /help for research ingestion
    raw_text = str(message.get("text") or message.get("caption") or "").strip()
    if raw_text.startswith("/start"):
        # Handle optional deep-link payload: /start <TOKEN>
        parts = raw_text.split(maxsplit=1)
        if len(parts) == 2:
            token = parts[1].strip()
            try:
                row = await db.fetchrow(
                    "SELECT user_id, expires_at, used FROM user_link_tokens WHERE token = $1",
                    token,
                )
                if row:
                    from datetime import datetime, timezone
                    if bool(row["used"]):
                        asyncio.create_task(_send_message(chat_id, "Link token already used. Please generate a new one from the website."))
                        return {"ok": "link_used"}
                    expires_at = row["expires_at"]
                    if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
                        asyncio.create_task(_send_message(chat_id, "Link token expired. Please generate a new one from the website."))
                        return {"ok": "link_expired"}
                    user = message.get("from") or {}
                    username = user.get("username") or ""
                    first_name = user.get("first_name") or ""
                    await db.execute(
                        """
                        INSERT INTO telegram_users (chat_id, username, first_name, linked_user_id, linked_at)
                        VALUES ($1, $2, $3, $4::uuid, now())
                        ON CONFLICT (chat_id) DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name, linked_user_id = EXCLUDED.linked_user_id, linked_at = now()
                        """,
                        chat_id,
                        username,
                        first_name,
                        str(row["user_id"]),
                    )
                    await db.execute("UPDATE user_link_tokens SET used = TRUE WHERE token = $1", token)
                    asyncio.create_task(_send_message(chat_id, "✅ Telegram linked. You can now send links, names, or screenshots to research."))
                    return {"ok": "linked"}
            except Exception:
                pass
        asyncio.create_task(_send_message(chat_id, "Welcome! Send me a tool name, a URL, or a screenshot to begin."))
        return {"ok": "ack_start"}
    if raw_text.startswith("/help"):
        asyncio.create_task(_send_message(chat_id, "Help: Send a tool name, URL, or screenshot. I'll research and summarize it for you."))
        return {"ok": "ack_help"}

    # Handle screenshot/photo first
    photo_list = message.get("photo") or []
    if isinstance(photo_list, list) and photo_list:
        # Pick the largest size (last entry)
        file_id = None
        try:
            file_id = photo_list[-1].get("file_id")
        except Exception:
            file_id = None
        if file_id and settings.telegram_bot_token:
            token = settings.telegram_bot_token.get_secret_value()
            api_base = f"https://api.telegram.org/bot{token}"
            async with httpx.AsyncClient(timeout=30) as client:
                try:
                    logger.info("[telegram] getFile chat_id=%s file_id=%s", chat_id, file_id)
                    gf = await client.get(f"{api_base}/getFile", params={"file_id": file_id})
                    file_path = gf.json().get("result", {}).get("file_path")
                    if file_path:
                        dl_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                        dl = await client.get(dl_url)
                        logger.info(
                            "[telegram] dl_file chat_id=%s path=%s status=%s ct=%s size=%s",
                            chat_id, file_path, dl.status_code, dl.headers.get("content-type"), len(dl.content),
                        )
                        img_bytes = dl.content
                        await _send_message(chat_id, "Analyzing screenshot…")
                        ocr_text = await ocr_image_to_text(img_bytes, mime_type=dl.headers.get("content-type") or "image/jpeg")
                        logger.info("[telegram] ocr_len=%d", len(ocr_text or ""))
                        prod = await extract_primary_product_name(ocr_text)
                        logger.info("[telegram] extracted_name='%s' plausible=%s", (prod or "")[:120], is_plausible_product_name(prod or ""))
                        if not prod or not is_plausible_product_name(prod):
                            await _send_message(chat_id, "I couldn't detect a valid product name in that screenshot. Please try again with a clearer image or send a link/name.")
                            return {"ok": "ocr_failed"}
                        await _send_message(chat_id, f"Scouting: {prod}\nStarting deep research…")
                        async def _process_image():
                            try:
                                # Look up linked user_id
                                uid_row = await db.fetchrow("SELECT linked_user_id FROM telegram_users WHERE chat_id = $1", chat_id)
                                uid = str(uid_row["linked_user_id"]) if uid_row and uid_row["linked_user_id"] else None
                                result = await run_ingest_flow_with_ocr(prod, ocr_text, source_label="telegram:screenshot", user_id=uid)
                                tool_id = result.get("tool_id")
                                link = _web_link_for_tool(str(tool_id))
                                if link:
                                    safe = html.escape(link, quote=True)
                                    await _send_message(
                                        chat_id,
                                        f'Done. You can check it <a href="{safe}">here</a>.',
                                        parse_mode="HTML",
                                        disable_web_page_preview=True,
                                    )
                                else:
                                    await _send_message(chat_id, "Done.")
                            except Exception:
                                await _send_message(chat_id, "Sorry, the research failed. Please try again later.")
                        asyncio.create_task(_process_image())
                        return {"ok": "accepted"}
                except Exception:
                    logger.exception("[telegram] error processing photo chat_id=%s", chat_id)
                    await _send_message(chat_id, "Sorry, I couldn't process that image.")
                    return {"ok": "error"}

    text, url = _extract_text_and_url(message)
    name: Optional[str] = None
    if url:
        try:
            url = canonicalize_url(url)
        except Exception:
            pass
    else:
        # Treat as tool name if not empty
        name = text

    # Notify user immediately and process asynchronously
    if url:
        asyncio.create_task(_send_message(chat_id, f"Scouting: {url}\nStarting deep research…"))
    elif name:
        asyncio.create_task(_send_message(chat_id, f"Scouting: {name}\nStarting deep research…"))
    else:
        asyncio.create_task(_send_message(chat_id, "Please send a tool name or URL to begin."))
        return {"ok": "ack"}

    async def _process():
        try:
            uid_row = await db.fetchrow("SELECT linked_user_id FROM telegram_users WHERE chat_id = $1", chat_id)
            uid = str(uid_row["linked_user_id"]) if uid_row and uid_row["linked_user_id"] else None
            result = await run_ingest_flow(url, name, False, uid)
            tool_id = result.get("tool_id")
            link = _web_link_for_tool(str(tool_id))
            if link:
                safe = html.escape(link, quote=True)
                await _send_message(
                    chat_id,
                    f'Done. You can check it <a href="{safe}">here</a>.',
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            else:
                await _send_message(chat_id, "Done.")
        except Exception as e:
            # Provide minimal diagnostic to help fix issues in non-production
            msg = "Sorry, the research failed. Please try again later."
            try:
                if settings.environment != "production":
                    detail = str(e)
                    if len(detail) > 180:
                        detail = detail[:180] + "…"
                    msg += f"\nError: {detail}"
            except Exception:
                pass
            await _send_message(chat_id, msg)

    asyncio.create_task(_process())
    return {"ok": "accepted"}


