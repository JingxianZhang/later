from __future__ import annotations
import base64
import logging
from typing import Optional
from openai import AsyncOpenAI
from .config import settings


logger = logging.getLogger(__name__)


def _detect_mime_from_bytes(data: bytes) -> str:
    try:
        if len(data) >= 4:
            # JPEG
            if data[0:2] == b"\xff\xd8":
                return "image/jpeg"
            # PNG
            if data[0:8] == b"\x89PNG\r\n\x1a\n":
                return "image/png"
            # GIF
            if data[0:6] in (b"GIF87a", b"GIF89a"):
                return "image/gif"
            # WEBP: RIFF....WEBP
            if data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
                return "image/webp"
    except Exception:
        pass
    return "image/jpeg"


def _sanitize_mime(mime_type: Optional[str], data: bytes) -> str:
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    mt = (mime_type or "").split(";")[0].strip().lower()
    if mt == "image/jpg":
        mt = "image/jpeg"
    if mt in allowed:
        return mt
    # Fallback to sniffed type
    sniffed = _detect_mime_from_bytes(data)
    if sniffed in allowed:
        return sniffed
    return "image/jpeg"


async def ocr_image_to_text(image_bytes: bytes, mime_type: Optional[str] = None) -> str:
    """
    Perform OCR on an image using the primary OpenAI vision-capable model.
    Returns plain text best-effort transcription of visible text.
    """
    if not image_bytes:
        return ""
    # Sanitize/normalize MIME to supported image types for the OpenAI data URL
    safe_mime = _sanitize_mime(mime_type, image_bytes)
    try:
        logger.info("[vision.ocr] start bytes=%d mime=%s model=%s", len(image_bytes), safe_mime, settings.model_primary)
    except Exception:
        pass
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{safe_mime};base64,{b64}"

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        completion = await client.chat.completions.create(
            model=settings.model_primary,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe all visible text from this image. Return plain text only."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.0,
        )
        text = completion.choices[0].message.content or ""
        try:
            logger.info("[vision.ocr] done text_len=%d", len(text))
        except Exception:
            pass
        return text
    except Exception as e:
        try:
            logger.exception("[vision.ocr] error: %s", str(e))
        except Exception:
            pass
        return ""


