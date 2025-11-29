import re


def is_plausible_product_name(name: str) -> bool:
    """
    Heuristic validator to prevent creating tools with junk/error messages.
    Accept names like 'Gamma', 'OpenAI', 'Cursor for Figma', 'Acme Studio'.
    Reject long paragraphs, URLs, error phrases, or overly punctuated strings.
    """
    if not name:
        return False
    s = " ".join(name.split())  # collapse whitespace/newlines
    if len(s) < 2 or len(s) > 80:
        return False
    low = s.lower()
    # Common error phrases we observed from OCR/noise
    if any(p in low for p in ["i'm sorry", "i cant assist", "i can't assist", "can't assist", "cannot assist"]):
        return False
    # Should not include URLs or obvious scheme
    if "http://" in low or "https://" in low or "www." in low:
        return False
    # Must contain at least one alphabetic character
    if not re.search(r"[a-zA-Z]", s):
        return False
    # Limit punctuation density
    punct = len(re.findall(r"[^\w\s\-&+.,]", s))
    if punct > 4:
        return False
    # Limit number of words to avoid paragraphs
    if len(s.split()) > 12:
        return False
    return True


def fallback_name_from_ocr(ocr_text: str) -> str:
    """
    Heuristic fallback to extract a short candidate name from OCR text.
    Strategy:
    - Take the first non-empty line
    - Strip quotes and excessive punctuation
    - Remove URLs
    - Truncate to first ~6 words / 48 chars
    """
    if not ocr_text:
        return ""
    # First non-empty line
    line = ""
    for l in ocr_text.splitlines():
        s = (l or "").strip()
        if s:
            line = s
            break
    if not line:
        return ""
    # Remove obvious URLs
    line = re.sub(r"https?://\S+", "", line, flags=re.IGNORECASE)
    # Strip wrapping quotes and excess punctuation
    line = line.strip(" '\"“”‘’–—-")
    # Collapse whitespace
    line = " ".join(line.split())
    # Truncate by words
    words = line.split()
    if len(words) > 6:
        line = " ".join(words[:6])
    # Hard cap length
    if len(line) > 48:
        line = line[:48]
    return line


