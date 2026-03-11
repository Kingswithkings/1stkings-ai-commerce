import json
from typing import Any
from app.db import (
    get_or_create_draft_order,
    update_order,
    get_order,
    get_state,
    set_state,
)
from app.catalog import Catalog


def _load_items(order: dict) -> list[dict]:
    try:
        return json.loads(order["items"])
    except Exception:
        return []


def _save_items(order_id: int, items: list[dict]):
    update_order(order_id, items=json.dumps(items))


def cart_totals(items: list[dict]) -> tuple[float, list[dict]]:
    total = 0.0
    enriched = []
    for it in items:
        line_total = float(it["qty"]) * float(it["unit_price"])
        total += line_total
        enriched.append({**it, "line_total": round(line_total, 2)})
    return round(total, 2), enriched


def add_items_to_cart(order_id: int, cart_items: list[dict], new_items: list[dict]) -> list[dict]:
    by_sku = {i["sku"]: i for i in cart_items}
    for n in new_items:
        sku = n["sku"]
        if sku in by_sku:
            by_sku[sku]["qty"] += int(n["qty"])
        else:
            by_sku[sku] = dict(n)

    merged = list(by_sku.values())
    _save_items(order_id, merged)
    return merged


def decrement_from_cart(order_id: int, cart_items: list[dict], query: str, dec: int = 1) -> tuple[list[dict], bool, str]:
    q = (query or "").lower().strip()
    if not q:
        return cart_items, False, "Tell me what to remove (e.g., 'remove rice')."

    dec = max(int(dec or 1), 1)

    new_items = []
    changed = False
    msg = ""

    for it in cart_items:
        if (not changed) and (q in it["name"].lower()):
            old_qty = int(it.get("qty", 0))
            new_qty = old_qty - dec

            if new_qty > 0:
                it2 = {**it, "qty": new_qty}
                new_items.append(it2)
                msg = f"Removed {dec} from {it['name']} (now {new_qty})."
            else:
                msg = f"Removed {it['name']} from your cart."
            changed = True
        else:
            new_items.append(it)

    if changed:
        _save_items(order_id, new_items)
        return new_items, True, msg

    return cart_items, False, "I couldn’t find that item in your cart."


def handle_chat(session_id: str, user_text: str, catalog: Catalog, store_slug: str = "naija-house") -> dict[str, Any]:
    state, ctx = get_state(session_id, store_slug)
    order = get_or_create_draft_order(session_id, store_slug)
    order_id = int(order["id"])
    items = _load_items(order)

    text = (user_text or "").strip()
    t_low = text.lower()

    # State machine for checkout fields
    if state == "checkout_wait_pickup_time":
        update_order(order_id, pickup_time=text, status="checkout")
        set_state(session_id, "checkout_wait_name", {"order_id": order_id}, store_slug)
        return _reply_with_cart(order_id, items, "Nice. What’s your name?")

    if state == "checkout_wait_name":
        update_order(order_id, customer_name=text)
        set_state(session_id, "checkout_wait_phone", {"order_id": order_id}, store_slug)
        return _reply_with_cart(order_id, items, "Thanks. What phone number should we contact you on?")

    if state == "checkout_wait_phone":
        update_order(order_id, customer_phone=text)
        set_state(session_id, "checkout_confirm", {"order_id": order_id}, store_slug)
        total, enriched = cart_totals(items)
        current_order = get_order(order_id)
        return {
            "reply": (
                f"Confirm your pickup order ✅\n"
                f"Name: {current_order.get('customer_name')}\n"
                f"Phone: {text}\n"
                f"Pickup: {current_order.get('pickup_time')}\n"
                f"Total: £{total}\n"
                f"Reply YES to confirm or CANCEL to stop."
            ),
            "cart": {"items": enriched, "total": total, "status": "checkout"},
            "needs_admin": False,
            "order_id": order_id,
        }

    if state == "checkout_confirm":
        if t_low in ["yes", "y", "confirm", "ok", "okay", "ok confirm", "confirm yes"]:
            update_order(order_id, status="confirmed")
            set_state(session_id, "browsing", {}, store_slug)
            total, enriched = cart_totals(items)
            current_order = get_order(order_id)
            return {
                "reply": (
                    f"Order confirmed ✅ (Order #{order_id})\n"
                    f"Pickup: {current_order.get('pickup_time')}\n"
                    f"Total: £{total}\n"
                    f"We’ll notify you when it’s ready."
                ),
                "cart": {"items": enriched, "total": total, "status": "confirmed"},
                "needs_admin": False,
                "order_id": order_id,
            }

        if "cancel" in t_low:
            update_order(order_id, status="cancelled")
            set_state(session_id, "browsing", {}, store_slug)
            return {
                "reply": "Cancelled. If you want to start again, just type what you need.",
                "cart": None,
                "needs_admin": False,
                "order_id": order_id,
            }

        total, enriched = cart_totals(items)
        return {
            "reply": f"Reply YES to confirm or CANCEL to stop. Total £{total}.",
            "cart": {"items": enriched, "total": total, "status": "checkout"},
            "needs_admin": False,
            "order_id": order_id,
        }

    # Normal intents
    from app.nlu import detect_intent, extract_items, parse_remove_command

    intent = detect_intent(text)

    if intent == "VIEW_CART":
        total, enriched = cart_totals(items)
        if not items:
            return {
                "reply": "Your cart is empty. Type what you want to buy.",
                "cart": {"items": [], "total": 0.0, "status": "draft"},
                "needs_admin": False,
                "order_id": order_id,
            }
        return {
            "reply": f"Here’s your cart 🛒 Total £{total}. Type CHECKOUT to finish.",
            "cart": {"items": enriched, "total": total, "status": order["status"]},
            "needs_admin": False,
            "order_id": order_id,
        }

    if intent == "CHECKOUT":
        if not items:
            return {
                "reply": "Your cart is empty. Add items first.",
                "cart": {"items": [], "total": 0.0, "status": "draft"},
                "needs_admin": False,
                "order_id": order_id,
            }
        set_state(session_id, "checkout_wait_pickup_time", {"order_id": order_id}, store_slug)
        update_order(order_id, status="checkout")
        return _reply_with_cart(order_id, items, "Great. What pickup time do you want? (e.g., Today 6pm)")

    if intent == "CANCEL":
        update_order(order_id, status="cancelled")
        set_state(session_id, "browsing", {}, store_slug)
        return {
            "reply": "Cancelled. If you want to start again, type what you need.",
            "cart": None,
            "needs_admin": False,
            "order_id": order_id,
        }

    if intent == "REMOVE":
        q, dec = parse_remove_command(text)
        new_items, changed, msg = decrement_from_cart(order_id, items, q, dec=dec)
        total, enriched = cart_totals(new_items)

        if not changed:
            return {
                "reply": f"{msg} Try: 'remove rice' or 'remove 2 rice'.",
                "cart": {"items": enriched, "total": total, "status": order["status"]},
                "needs_admin": False,
                "order_id": order_id,
            }

        return {
            "reply": f"{msg} New total £{total}.",
            "cart": {"items": enriched, "total": total, "status": order["status"]},
            "needs_admin": False,
            "order_id": order_id,
        }

    # ADD_OR_SEARCH
    parsed = extract_items(text)
    matched_new = []
    needs_admin = False
    flagged = 0
    clarifications = []

    for p in parsed:
        prod, score, top5 = catalog.match(p.raw_name)

        if (prod is None) or (score < 0.35):
            needs_admin = True
            flagged = 1
            sugg = ", ".join([x[0].name for x in top5[:3]]) if top5 else ""
            if sugg:
                clarifications.append(f"‘{p.raw_name}’ not clear. Did you mean: {sugg}?")
            else:
                clarifications.append(f"‘{p.raw_name}’ not found. Try a different name.")
            continue

        if prod.in_stock <= 0:
            needs_admin = True
            flagged = 1
            clarifications.append(f"{prod.name} is currently out of stock.")
            continue

        matched_new.append({
            "sku": prod.sku,
            "name": prod.name,
            "qty": int(p.qty),
            "unit": prod.unit,
            "unit_price": float(prod.price),
        })

    if flagged:
        update_order(order_id, flagged=1)

    if matched_new:
        items = add_items_to_cart(order_id, items, matched_new)

    total, enriched = cart_totals(items)

    if needs_admin and not matched_new and clarifications:
        return {
            "reply": "I need a bit more detail:\n- " + "\n- ".join(clarifications) + "\n\nOr type 'show cart' / 'checkout'.",
            "cart": {"items": enriched, "total": total, "status": order["status"]},
            "needs_admin": True,
            "order_id": order_id,
        }

    note = ("\n\nNotes:\n- " + "\n- ".join(clarifications)) if clarifications else ""

    if not items:
        return {
            "reply": "Tell me what you want to buy.",
            "cart": {"items": [], "total": 0.0, "status": "draft"},
            "needs_admin": False,
            "order_id": order_id,
        }

    return {
        "reply": f"Added ✅. Cart total £{total}. Type 'show cart' or 'checkout' to finish.{note}",
        "cart": {"items": enriched, "total": total, "status": order["status"]},
        "needs_admin": bool(flagged),
        "order_id": order_id,
    }


def _reply_with_cart(order_id: int, items: list[dict], msg: str) -> dict:
    total, enriched = cart_totals(items)
    return {
        "reply": msg,
        "cart": {"items": enriched, "total": total, "status": get_order(order_id)["status"]},
        "needs_admin": False,
        "order_id": order_id,
    }