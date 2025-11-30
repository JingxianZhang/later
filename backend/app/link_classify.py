from __future__ import annotations
from typing import Literal
from urllib.parse import urlparse, parse_qs
import asyncio
from .scrape import fetch_clean_text

LinkKind = Literal["video_youtube", "video_tiktok", "social", "podcast", "article_or_homepage"]


def classify_link(url: str) -> LinkKind:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    if not host:
        return "article_or_homepage"
    if "youtube.com" in host or "youtu.be" in host:
        return "video_youtube"
    if "tiktok.com" in host:
        return "video_tiktok"
    if any(h in host for h in ["x.com", "twitter.com", "linkedin.com"]):
        return "social"
    if any(h in host for h in ["spotify.com", "podcasts.google", "podcasts.apple", "buzzsprout", "simplecast", "anchor.fm", "megaphone.fm", "transistor.fm", "castbox.fm"]):
        return "podcast"
    return "article_or_homepage"


def _youtube_id(url: str) -> str:
    try:
        p = urlparse(url)
        if "youtu.be" in (p.hostname or ""):
            return (p.path or "/").strip("/").split("/")[0]
        q = parse_qs(p.query)
        vid = q.get("v", [""])[0]
        if not vid and (p.path or "").startswith("/shorts/"):
            vid = (p.path or "/").split("/")[2] if len((p.path or "/").split("/")) > 2 else ""
        return vid
    except Exception:
        return ""


async def _youtube_transcript_text(video_id: str) -> str:
    if not video_id:
        return ""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception:
        return ""
    try:
        # youtube-transcript-api is blocking; run in a thread
        segments = await asyncio.to_thread(YouTubeTranscriptApi.get_transcript, video_id)
        # Each segment: {"text": "...", "start": ..., "duration": ...}
        lines = [seg.get("text") or "" for seg in segments if seg.get("text")]
        text = "\n".join(lines)
        return text[:200_000]
    except Exception:
        return ""


async def fetch_text_for_url(url: str) -> str:
    """
    Fetch content for a URL based on its kind. Prefer transcripts for YouTube.
    Fallback to generic clean-text scraper.
    """
    kind = classify_link(url)
    if kind == "video_youtube":
        vid = _youtube_id(url)
        tx = await _youtube_transcript_text(vid)
        if tx:
            return tx
        # fallback to normal fetch
        return await fetch_clean_text(url)
    if kind == "podcast":
        # For now, fetch the episode/show-notes page; transcripts can be added later via API
        return await fetch_clean_text(url)
    # social and default: normal fetch (social may be low-signal; augmentation handles highlights)
    return await fetch_clean_text(url)



