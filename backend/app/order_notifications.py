import json

from app.db import SessionLocal, get_order
from app.models import Store
from app.whatsapp_client import send_store_whatsapp_text


def _load_items(order: dict) -> list[dict]:
    try:
        return json.loads(order.get("items") or "[]")
    except (TypeError, json.JSONDecodeError):
        return []


def _build_order_notification_message(store: Store, order: dict) -> str:
    items = _load_items(order)
    lines = [
        f"New order for {store.name}",
        f"Order #{order['id']}",
    ]

    if order.get("customer_name"):
        lines.append(f"Customer: {order['customer_name']}")
    if order.get("customer_phone"):
        lines.append(f"Phone: {order['customer_phone']}")
    if order.get("fulfillment_type"):
        lines.append(f"Fulfillment: {str(order['fulfillment_type']).title()}")
    if order.get("pickup_time"):
        lines.append(f"Pickup: {order['pickup_time']}")
    if order.get("delivery_address"):
        lines.append(f"Delivery address: {order['delivery_address']}")

    if items:
        lines.append("Items:")
        total = 0.0
        for item in items:
            qty = int(item.get("qty") or 0)
            unit_price = float(item.get("unit_price") or 0.0)
            line_total = round(qty * unit_price, 2)
            total += line_total
            lines.append(f"- {qty} x {item.get('name', 'Item')} = GBP {line_total:.2f}")
        lines.append(f"Total: GBP {total:.2f}")

    channel = str(order.get("channel") or "").strip()
    if channel:
        lines.append(f"Channel: {channel}")

    return "\n".join(lines)[:1024]


def send_new_order_notification(order_id: int) -> bool:
    order = get_order(order_id)
    if not order or order.get("status") != "confirmed":
        return False

    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.slug == order["store_slug"]).first()
        if not store:
            return False

        recipient = (getattr(store, "order_notification_number", None) or "").strip()
        if not recipient or not bool(store.whatsapp_enabled):
            return False

        message = _build_order_notification_message(store, order)
        provider_key = (
            (store.whatsapp_bot_id or "").strip()
            if (store.whatsapp_provider or "meta").strip().lower() == "sendpulse"
            else (store.whatsapp_phone_number_id or "").strip()
        )
        return send_store_whatsapp_text(store, provider_key, recipient, message)
    finally:
        db.close()
