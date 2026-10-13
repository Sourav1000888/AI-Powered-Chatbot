import json
from datetime import date
from openai import AsyncOpenAI

from config import BASE_URL, MAX_SEARCH_ROUNDS, SYSTEM_PROMPT, TEXT_MODEL, VISION_MODEL, OPENROUTER_API_KEY
from services.search import SearchError, format_results, web_search

client = AsyncOpenAI(base_url=BASE_URL, api_key=OPENRUTER_API_KEY)

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current or uncertain information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Short search query"}
            },
            "required": ["query"],
        },
    },
}


def has_images(messages: list[dict]) -> bool:
    return any(
        isinstance(m["content"], list)
        and any(b.get("type") == "image" for b in m["content"])
        for m in messages
    )




async def stream_chat(messages: list[dict]):
    vision = has_images(messages)
    model = VISION_MODEL if vision else TEXT_MODEL
    system = f"{SYSTEM_PROMPT}\nToday's date: {date.today():%d %B %Y}."
    chat = [{"role": "system", "content": system}] #system instruction
    chat.extend(messages)  
    sources: list[dict] = []

    for round_no in range(MAX_SEARCH_ROUNDS + 1):
        kwargs = {"model": model, "messages": chat, "stream": True}
        # Vision model (gemma3) tools support nahi karta; aakhri round mein bhi tools band
        if not vision and round_no < MAX_SEARCH_ROUNDS:
            kwargs["tools"] = [SEARCH_TOOL]

        stream = await client.chat.completions.create(**kwargs)

        text = ""
        calls: dict[int, dict] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text += delta.content
                yield {"text": delta.content}
            for tc in delta.tool_calls or []:
                slot = calls.setdefault(
                    tc.index or 0,
                    {"id": "", "name": "", "args": ""}
                )

                if tc.id:
                    slot["id"] = tc.id

                if tc.function:
                    if tc.function.name:
                        slot["name"] = tc.function.name

                    if tc.function.arguments:
                        slot["args"] += tc.function.arguments

        if not calls:
            break  # model ne seedha jawab de diya

        ordered = [calls[i] for i in sorted(calls)]
        for n, c in enumerate(ordered):
            c["id"] = c["id"] or f"call_{round_no}_{n}"
            c["args"] = c["args"] or "{}"

        chat.append(
            {
                "role": "assistant",
                "content": text or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["args"]},
                    }
                    for c in ordered
                ],
            }
        )

        for c in ordered:
            try:
                args = json.loads(c["args"])
            except json.JSONDecodeError:
                args = {}
            query = str(args.get("query", "")).strip()

            if c["name"] != "web_search" or not query:
                result = "Error: call web_search with a non-empty 'query'."
            else:
                yield {"status": "searching", "query": query}
                try:
                    found = await web_search(query)
                    sources.extend(found)
                    result = format_results(found)
                except SearchError as e:
                    result = f"Search failed ({e}). Tell the user search is unavailable."
            chat.append({"role": "tool", "tool_call_id": c["id"], "content": result})

        yield {"status": "answering"}

    if sources:
        seen, unique = set(), []
        for s in sources:
            if s["url"] and s["url"] not in seen:
                seen.add(s["url"])
                unique.append({"title": s["title"], "url": s["url"]})
        yield {"sources": unique}