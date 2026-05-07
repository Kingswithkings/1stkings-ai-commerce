import re
from dataclasses import dataclass

@dataclass
class ParsedItem:
    raw_name: str
    qty: int


def detect_intent(text: str) -> str:
    t = (text or "").lower().strip()

    if any(x in t for x in ["help", "human", "agent", "admin", "call you"]):
        return "HUMAN_HELP"
    if any(x in t for x in ["show cart", "my cart", "view cart", "cart"]):
        return "VIEW_CART"
    if any(x in t for x in ["checkout", "check out", "pay", "confirm order"]):
        return "CHECKOUT"
    if t in ["yes", "y", "confirm", "ok confirm", "confirm yes", "ok", "okay"]:
        return "CONFIRM"
    if any(x in t for x in ["cancel", "stop", "never mind"]):
        return "CANCEL"
    if any(x in t for x in ["remove", "delete"]):
        return "REMOVE"
    if any(x in t for x in ["change", "update", "set qty", "set quantity"]):
        return "UPDATE"
    return "ADD_OR_SEARCH"


def is_general_query(text: str) -> bool:
    t = (text or "").lower().strip()
    if not t:
        return False

    if "?" in t:
        return True

    general_starts = [
        "what",
        "who",
        "when",
        "where",
        "why",
        "how",
        "tell me",
        "explain",
        "define",
        "can you",
        "do you",
        "is it",
        "are there",
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "tell me a",
        "give me",
        "i need",
        "i want",
    ]
    return any(t.startswith(prefix) for prefix in general_starts)


# -------------------------
# ADD parsing
# -------------------------
_qty_prefix = re.compile(r"^\s*(\d+)\s+(.+)$")
_qty_x = re.compile(r"(.+?)\s*[xX]\s*(\d+)\s*$")

def extract_items(text: str) -> list[ParsedItem]:
    """
    Heuristic parser:
    - Splits by 'and' / ',' to get chunks
    - Supports: "2 indomie", "indomie x2"
    - Default qty = 1
    """
    t = (text or "").strip()
    chunks = re.split(r"\s*(?:,| and )\s*", t, flags=re.IGNORECASE)
    items: list[ParsedItem] = []

    for c in chunks:
        c = c.strip()
        if not c:
            continue

        m1 = _qty_prefix.match(c)
        if m1:
            qty = int(m1.group(1))
            name = m1.group(2).strip()
            items.append(ParsedItem(raw_name=name, qty=max(qty, 1)))
            continue

        m2 = _qty_x.match(c)
        if m2:
            name = m2.group(1).strip()
            qty = int(m2.group(2))
            items.append(ParsedItem(raw_name=name, qty=max(qty, 1)))
            continue

        items.append(ParsedItem(raw_name=c, qty=1))

    return items


# -------------------------
# REMOVE parsing (decrement)
# -------------------------
_remove_cmd = re.compile(r"^\s*(remove|delete)\s+(.*)$", re.IGNORECASE)
_remove_qty_prefix = re.compile(r"^\s*(\d+)\s+(.+)$")

def parse_remove_command(text: str) -> tuple[str, int]:
    """
    Supports:
      - "remove rice" -> ("rice", 1)
      - "remove 2 rice" -> ("rice", 2)
      - "delete tomatoes" -> ("tomatoes", 1)
    """
    t = (text or "").strip()
    m = _remove_cmd.match(t)
    if not m:
        return "", 0

    rest = (m.group(2) or "").strip()
    if not rest:
        return "", 0

    m2 = _remove_qty_prefix.match(rest)
    if m2:
        qty = int(m2.group(1))
        name = (m2.group(2) or "").strip()
        return name, max(qty, 1)

    return rest, 1