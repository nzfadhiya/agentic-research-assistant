from ddgs import DDGS

def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo.
    Returns a list of results with title, url, and body.
    """
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "body": r.get("body", "")
            })
    return results