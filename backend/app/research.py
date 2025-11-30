from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from .config import settings


SYSTEM_PROMPT = (
    "You are a meticulous research assistant. Given aggregated research text from the official site, docs/blog, and recent articles, "
    "synthesize a concise JSON fact sheet with keys:\n"
    "- product_name: string (short, canonical product or company name)\n"
    "- overview: string\n"
    "- features: array of 6-10 short, benefit-oriented bullets (avoid fluff)\n"
    "- pricing: object mapping plan/tier to a concise price string (if no pricing found, return {})\n"
    "- tech_stack: array of relevant technologies mentioned\n"
    "- competitors: array of short names (include only if clearly implied by sources)\n"
    "- integrations: array of integration partners/tools if clearly mentioned; else []\n"
    "- how_to_use: array of 3-6 concise, practical steps or tips (only if strong signals exist)\n"
    "- use_cases: array of 3-6 short scenarios describing when/why to use the tool (only if supported)\n"
    "- user_feedback: array of 3-6 paraphrased insights that sound like user feedback with brief qualifiers (only if supported)\n"
    "- recent_updates: array of 3-6 bullets summarizing notable updates/news. Each bullet MUST begin with a month-level date in the format [YYYY-MM] when possible (e.g., \"[2025-06] Changed pricing…\"). Prefer items within the last 12–18 months.\n"
    "Rules:\n"
    "- Use only verifiable facts present in the text; prefer concrete details (caps, integrations, pricing signals) over generic marketing.\n"
    "- Do not hallucinate.\n"
    "- If a section is not supported by evidence, return an empty array/object for that section (do not invent).\n"
    "- Keep content succinct but informative for an evaluator.\n"
    "Pricing normalization rules:\n"
    "- For each plan/tier, return a SINGLE short string suitable for UI display, e.g., 'Free', '$19/mo', '$99/user/mo', 'Custom', '$199/yr'.\n"
    "- Normalize units and wording: use '/mo' for monthly, '/yr' for yearly, '/user' or '/seat' for per-user pricing. Prefer '$' currency symbol when USD is implied; include currency code if not USD (e.g., '€29/mo').\n"
    "- If key qualifiers are essential (e.g., 'billed annually', '7‑day trial', 'includes X credits'), append AFTER an em dash: ' — billed annually' or ' — includes 10k credits'. Keep the qualifier ≤ 12 words.\n"
    "- Do NOT output paragraphs or long sentences in pricing. Avoid generic marketing language; include only factual pricing terms.\n"
    "- If pricing is not public or only 'contact sales', return 'Custom'.\n"
    "- If uncertain or no pricing is present, return {} for the entire pricing object."
)


async def synthesize_one_pager(
    clean_text: str,
    ocr_text: Optional[str] = None,
    screenshot_intent: Optional[str] = None,
) -> Dict[str, Any]:
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    intent_hint = ""
    if screenshot_intent:
        intent_hint = (
            "Screenshot intent: "
            + screenshot_intent
            + ". If 'how_to_use', prioritize filling 'how_to_use' with specific steps/examples. "
              "If 'new_features', prioritize updating 'features' and 'recent_updates' with those details. "
              "If 'general_intro', treat as normal research.\n"
        )
    ocr_hint = ""
    if ocr_text:
        ocr_hint = "OCR excerpt (user-provided screenshot; prioritize if relevant):\n" + ocr_text[:4000] + "\n\n"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    completion = await client.chat.completions.create(
        model=settings.model_primary,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (f"Today's date: {today_str}\n" + intent_hint + ocr_hint + "Combined research text:\n" + clean_text[:12000]),
            },
        ],
        temperature=0.2,
    )
    content = completion.choices[0].message.content or "{}"
    import json

    data = json.loads(content)
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    return data


async def pick_five_claims(one_pager: Dict[str, Any]) -> List[str]:
    # Naive heuristic: pick first few items from features and pricing keys
    claims: List[str] = []
    for f in (one_pager.get("features") or [])[:2]:
        claims.append(f"Feature: {f}")
    for k, v in list((one_pager.get("pricing") or {}).items())[:1]:
        claims.append(f"Pricing {k}: {v}")
    return claims[:3]


async def resolve_pricing_via_llm(name: str, snippets: List[str]) -> Dict[str, str]:
    """
    Given snippets likely from pricing pages, extract a structured pricing object.
    """
    if not snippets:
        return {}
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    SYSTEM = (
        "Extract pricing from provided text. Return a JSON object mapping plan/tier names to a SINGLE concise price string per tier.\n"
        "Formatting rules:\n"
        "- Use compact, normalized forms like: 'Free', '$19/mo', '$99/user/mo', '$199/yr', 'Custom'.\n"
        "- Normalize wording: '/mo' for monthly, '/yr' for yearly, '/user' or '/seat' for per-user. Prefer '$' when USD; otherwise include currency symbol/code.\n"
        "- If a short qualifier is essential (e.g., 'billed annually', 'includes 10k credits'), append AFTER an em dash: ' — billed annually'. Max 12 words.\n"
        "- Do NOT output paragraphs; avoid generic marketing. Include only factual pricing terms.\n"
        "- If no pricing is present, return {}. Do not hallucinate."
    )
    joined = "\n\n".join(snippets)[:12000]
    completion = await client.chat.completions.create(
        model=settings.model_light,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Product: {name}\n\nText:\n{joined}"},
        ],
        temperature=0.0,
    )
    import json as _json
    try:
        return _json.loads(completion.choices[0].message.content or "{}")
    except Exception:
        return {}


async def resolve_official_site_via_llm(name: str, candidates: List[str]) -> str:
    """
    Ask the LLM to pick the single official homepage URL for the product.
    Returns empty string if uncertain.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    SYSTEM = (
        "You identify the single official product homepage. "
        "Rules:\n"
        "- Return ONLY an https homepage for the most notable/commonly-referenced product or company matching the name (apex domain or '/').\n"
        "- NEVER return social profiles (x.com/twitter.com, linkedin.com, youtube.com, tiktok.com), press pages, app store pages, or docs subdomains.\n"
        "- Prefer globally recognized entities over local/obscure namesakes. Consider candidate titles/snippets; prefer domains that have docs/blog/news pages and broad references.\n"
        "- If multiple valid, prefer .com/.ai over .net/.io when ambiguous.\n"
        "- If uncertain, return an empty official_url.\n"
        'Respond in strict JSON: {"official_url": "https://example.com"}'
    )
    user = f"Product name: {name}\nCandidate references (may include noise):\n- " + "\n- ".join(candidates[:15])
    completion = await client.chat.completions.create(
        model=settings.model_light,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
    )
    content = completion.choices[0].message.content or "{}"
    import json  # local import to keep file self-contained
    try:
        data = json.loads(content)
        url = str(data.get("official_url") or "").strip()
        return url
    except Exception:
        return ""


async def extract_primary_product_name(ocr_text: str, hint: str | None = None) -> str:
    """
    Given OCR'd text from a screenshot, extract the single most likely product/tool/company name.
    Returns a concise name suitable for downstream resolution.
    """
    if not ocr_text:
        return (hint or "").strip()
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    SYSTEM = (
        "From the provided text (likely from a screenshot), return the single most likely product/tool/company name.\n"
        "Rules:\n"
        "- Return only the concise name, no extra words.\n"
        "- Prefer the brand/product mentioned in titles, headers, or pricing tables.\n"
        "- If multiple, pick the most prominent or central one.\n"
        "- If uncertain, return an empty string."
    )
    user = (hint + "\n\n" if hint else "") + ocr_text[:8000]
    completion = await client.chat.completions.create(
        model=settings.model_light,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
    )
    name = (completion.choices[0].message.content or "").strip()
    # Keep name to a modest length to avoid passing long junk to resolution
    return name[:120]


async def classify_screenshot_intent(ocr_text: str) -> str:
    """
    Classify OCR text into one of: 'how_to_use', 'new_features', 'general_intro'.
    """
    if not ocr_text or len(ocr_text.strip()) < 20:
        return "general_intro"
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    SYSTEM = (
        "Classify the user-provided screenshot text into one of: how_to_use, new_features, general_intro.\n"
        "- how_to_use: step-like instructions, tips, examples, 'press', 'click', 'use X to', 'how to', 'shortcut', 'you can do...', etc.\n"
        "- new_features: release notes, new capabilities, 'introducing', 'now supports', 'vX.Y', 'changelog'.\n"
        "- general_intro: general descriptions or marketing copy with no clear instruction or new-feature emphasis."
    )
    completion = await client.chat.completions.create(
        model=settings.model_light,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": ocr_text[:2000]},
        ],
        temperature=0.0,
    )
    label = (completion.choices[0].message.content or "").strip().lower()
    if "how_to_use" in label or "how to use" in label or "how_to" in label or "howto" in label:
        return "how_to_use"
    if "new_features" in label or "new features" in label or "release" in label or "changelog" in label:
        return "new_features"
    return "general_intro"


def normalize_and_sort_recent_updates(one_pager: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sort recent_updates by detected date (YYYY-MM or YYYY-MM-DD) descending.
    If no date is present, leave ordering at the end.
    """
    import re
    updates = one_pager.get("recent_updates") or []
    if not isinstance(updates, list) or not updates:
        return one_pager
    def key(s: str):
        m = re.search(r"(\d{4})-(\d{2})(?:-(\d{2}))?", s)
        if not m:
            return (0, 0, 0)
        y = int(m.group(1)); mo = int(m.group(2)); d = int(m.group(3) or 1)
        return (y, mo, d)
    updates_sorted = sorted([str(u) for u in updates], key=key, reverse=True)
    one_pager["recent_updates"] = updates_sorted
    return one_pager


