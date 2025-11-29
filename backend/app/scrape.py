import httpx
import re
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential_jitter


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4))
async def fetch_clean_text(url: str) -> str:
    # Fetch HTML then extract visible text
    headers = {
        # Use a common desktop UA to reduce 403/anti-bot blocks
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    print(f"[scrape] GET {url}")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            print(f"[scrape] GET {url} -> {resp.status_code}")
            resp.raise_for_status()
        except Exception as e:
            # Log a short body snippet for diagnostics
            body_preview = ""
            try:
                body_preview = (resp.text or "")[:200]  # type: ignore[name-defined]
            except Exception:
                pass
            print(f"[scrape] ERROR fetching {url}: {type(e).__name__} {str(e)} {body_preview}")
            # Fallback via r.jina.ai plaintext proxy (helps with JS/protected sites)
            try:
                from urllib.parse import urlparse, urlunparse
                p = urlparse(url)
                scheme = p.scheme or "https"
                target = f"https://r.jina.ai/{scheme}://{p.netloc}{p.path or ''}"
                if p.query:
                    target = target + "?" + p.query
                print(f"[scrape] FALLBACK GET {target}")
                fb = await client.get(target, headers=headers, follow_redirects=True)
                print(f"[scrape] FALLBACK GET {target} -> {fb.status_code}")
                fb.raise_for_status()
                html = fb.text
            except Exception as e2:
                print(f"[scrape] FALLBACK ERROR {type(e2).__name__} {str(e2)}")
                raise
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    # remove non-content
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # collapse whitespace and drop very short lines
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if len(ln) >= 3]
    cleaned = "\n".join(lines)
    return cleaned[:200_000]  # cap to avoid overly large prompts

