from typing import List, Tuple
from tavily import TavilyClient
from .config import settings


async def verify_claims(claims: List[str]) -> List[Tuple[str, bool, str]]:
    """
    Returns list of (claim, verified, citation_url)
    """
    # Simple synchronous Tavily client; wrap per-claim for MVP
    client = TavilyClient(api_key=(settings.tavily_api_key.get_secret_value() if settings.tavily_api_key else ""))
    results: List[Tuple[str, bool, str]] = []
    for c in claims:
        try:
            r = client.search(query=c, max_results=3)
            url = r["results"][0]["url"] if r.get("results") else ""
            results.append((c, True if url else False, url))
        except Exception:
            results.append((c, False, ""))
    return results[:5]


