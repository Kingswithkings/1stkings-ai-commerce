from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.catalog import load_catalog_for_store
from app.db import SessionLocal, log_message
from app.models import Store
from app.order_flow import handle_chat
from app.whatsapp_client import send_store_whatsapp_text

router = APIRouter(prefix="/channels/whatsapp", tags=["whatsapp"])


def _find_store(
    db: Session,
    provider_key: str | None = None,
    store_slug: str | None = None,
) -> Store | None:
    if provider_key:
        store = (
            db.query(Store)
            .filter(Store.whatsapp_phone_number_id == provider_key)
            .first()
        )
        if store:
            return store

        store = (
            db.query(Store)
            .filter(Store.whatsapp_bot_id == provider_key)
            .first()
        )
        if store:
            return store

    if store_slug:
        return db.query(Store).filter(Store.slug == store_slug).first()

    return None


def _reply_for_message(
    db: Session,
    store: Store,
    customer_id: str,
    text_body: str,
    provider_key: str = "",
) -> dict[str, Any]:
    catalog = load_catalog_for_store(store.slug)
    log_message(customer_id, "user", text_body, store.slug, "whatsapp")
    result = handle_chat(
        session_id=customer_id,
        user_text=text_body,
        catalog=catalog,
        store_slug=store.slug,
        channel="whatsapp",
    )
    log_message(
        customer_id,
        "assistant",
        result["reply"],
        store.slug,
        "whatsapp",
    )
    send_store_whatsapp_text(store, provider_key, customer_id, result["reply"])
    return {
        "to": customer_id,
        "reply": result["reply"],
        "order_id": result["order_id"],
        "store_slug": store.slug,
    }


def _handle_meta_payload(db: Session, payload: dict[str, Any], store_slug: str | None) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = (metadata.get("phone_number_id") or "").strip()
            store = _find_store(db, provider_key=phone_number_id, store_slug=store_slug)
            if not store or not store.whatsapp_enabled:
                continue

            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                customer_wa_id = (message.get("from") or "").strip()
                text_body = (message.get("text", {}).get("body", "") or "").strip()
                if not customer_wa_id or not text_body:
                    continue
                replies.append(
                    _reply_for_message(db, store, customer_wa_id, text_body, phone_number_id)
                )
    return replies


def _extract_sendpulse_message(payload: dict[str, Any] | list[Any]) -> tuple[str, str, str]:
    event = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(event, dict):
        return "", "", ""

    contact = event.get("contact", {}) or {}
    last_message_data = contact.get("last_message_data", {}) or {}
    nested_message = last_message_data.get("message", {}) or {}

    bot_id = (
        event.get("bot_id")
        or event.get("bot", {}).get("id")
        or event.get("chatbot", {}).get("id")
        or event.get("channel", {}).get("id")
        or ""
    )
    phone = (
        event.get("phone")
        or contact.get("phone")
        or event.get("subscriber", {}).get("phone")
        or event.get("chat", {}).get("contact", {}).get("phone")
        or ""
    )
    message = event.get("message") or nested_message
    if isinstance(message, dict):
        text_body = (
            message.get("text")
            or message.get("body")
            or message.get("message")
            or ""
        )
        if isinstance(text_body, dict):
            text_body = text_body.get("body") or text_body.get("text") or ""
    else:
        text_body = (
            message
            or event.get("text")
            or event.get("body")
            or contact.get("last_message")
            or ""
        )

    return str(bot_id).strip(), str(phone).strip(), str(text_body).strip()


def _handle_sendpulse_payload(
    db: Session,
    payload: dict[str, Any],
    store_slug: str | None,
) -> list[dict[str, Any]]:
    bot_id, customer_phone, text_body = _extract_sendpulse_message(payload)
    if not customer_phone or not text_body:
        return []

    store = _find_store(db, provider_key=bot_id, store_slug=store_slug)
    if not store or not store.whatsapp_enabled:
        return []

    return [_reply_for_message(db, store, customer_phone, text_body, bot_id)]


@router.get("/webhook")
def verify_webhook(
    request: Request,
    mode: str = Query("", alias="hub.mode"),
    verify_token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
    store_slug: str | None = Query(None),
):
    if mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")

    db: Session = SessionLocal()
    try:
        store = _find_store(db, store_slug=store_slug)
    finally:
        db.close()

    expected = (
        (store.whatsapp_verify_token if store else None)
        or os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    )

    if not expected or verify_token != expected:
        raise HTTPException(status_code=403, detail="Invalid verify token")

    return PlainTextResponse(content=challenge)


@router.post("/webhook")
async def whatsapp_webhook(request: Request, store_slug: str | None = Query(None)):
    payload = await request.json()
    db: Session = SessionLocal()

    try:
        if isinstance(payload, dict) and isinstance(payload.get("entry"), list):
            replies = _handle_meta_payload(db, payload, store_slug)
            return {"ok": True, "provider": "meta", "processed": len(replies), "replies": replies}

        replies = _handle_sendpulse_payload(db, payload, store_slug)
        return {
            "ok": True,
            "provider": "sendpulse",
            "processed": len(replies),
            "replies": replies,
        }
    finally:
        db.close()
