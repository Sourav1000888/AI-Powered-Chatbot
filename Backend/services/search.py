import httpx
from config import OPENROUTER_API_KEY, SEARCH_MAX_RESULTS, SEARCH_URL


class SearchError(Exception):
    pass


async def web_search(query: str) -> list[dict]:
    if not OLLAMA_API_KEY:
        raise SearchError("API_KEY not initialize in .env file")
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
                json={"query": query, "max_results": SEARCH_MAX_RESULTS},
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        raise SearchError(type(e).__name__)

    results = []
    for item in data.get("results", []):
        url = item.get("url", "")
        results.append(
            {
                "title": item.get("title") or url,
                "url": url,
                # chhota model hai, isliye context bachane ke liye trim
                "content": (item.get("content") or "")[:800],
                #also fetch score
            }
        )
    return results


def format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."
    return "\n\n".join(
        f"[{i}] {r['title']}\n{r['url']}\n{r['content']}"
        for i, r in enumerate(results, 1)
    )