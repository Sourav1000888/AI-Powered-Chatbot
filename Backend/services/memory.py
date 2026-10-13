from collections import OrderedDict

MAX_MESSAGES = 10      
MAX_SESSIONS = 100     
MAX_IMAGES_KEPT = 3    
PLACEHOLDER = "[Old images removed]"

_sessions: "OrderedDict[str, list[dict]]" = OrderedDict()


def _is_image(block) -> bool:
    return isinstance(block, dict) and block.get("type") == "image"


def _strip_old_images(history: list[dict]) -> None:
    """Latest MAX_IMAGES_KEPT images keep. and remove other"""
    kept = 0
    for msg in reversed(history):
        content = msg["content"]
        if not isinstance(content, list):
            continue
        for i in range(len(content) - 1, -1, -1):
            if _is_image(content[i]):
                kept += 1
                if kept > MAX_IMAGES_KEPT:
                    content[i] = {"type": "text", "text": PLACEHOLDER}


def get_history(session_id: str) -> list[dict]:
    """to send llm with images"""
    return list(_sessions.get(session_id, []))


def get_display_history(session_id: str) -> list[dict]:
    """for sending browser (not base64, only text + image count)."""
    out = []
    for m in _sessions.get(session_id, []):
        content = m["content"]
        if isinstance(content, str):
            text, n_images = content, 0
        else:
            n_images = sum(1 for b in content if _is_image(b))
            text = " ".join(
                b["text"]
                for b in content
                if b.get("type") == "text" and b["text"] != PLACEHOLDER
            )
        out.append({"role": m["role"], "text": text, "image_count": n_images})
    return out


def add_exchange(session_id: str, user_content, assistant_text: str) -> None:
    """user_content: str ya content-blocks list. adding in history """
    history = _sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": assistant_text})

    if len(history) > MAX_MESSAGES:
        del history[: len(history) - MAX_MESSAGES]
    while history and history[0]["role"] != "user":
        history.pop(0)

    _strip_old_images(history)

    _sessions.move_to_end(session_id)
    while len(_sessions) > MAX_SESSIONS:
        _sessions.popitem(last=False)


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)