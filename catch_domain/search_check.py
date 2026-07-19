"""Stage 3: exact-match web presence via DuckDuckGo (ddgs, unofficial)."""
from ddgs import DDGS


def search_presence(name: str) -> tuple[list[dict], str]:
    """Search DuckDuckGo for '"<name>"'; keep hits mentioning the name.

    ddgs raises library-specific errors on throttling; any failure means
    'pending' (retry on a later run) rather than crashing the pipeline.
    """
    try:
        raw = DDGS().text(f'"{name}"', max_results=10)
    except Exception:
        return [], "pending"
    hits = []
    for item in raw or []:
        title = item.get("title", "")
        url = item.get("href", "")
        if name in title.lower() or name in url.lower():
            hits.append({"title": title, "url": url})
    return hits, "done"
