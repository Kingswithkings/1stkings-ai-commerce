import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.catalog import load_catalog_for_store
from app.db import SessionLocal, log_message
from app.models import Store
from app.order_flow import handle_chat

router = APIRouter(prefix="/channels/whatsapp", tags=["whatsapp"])

_sendpulse_token_cache: dict[str, Any] = {"access_token": "", "expires_at": 0.0}


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any] | None:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def _send_meta_whatsapp_text(phone_number_id: str, to: str, body: str) -> bool:
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    api_version = os.getenv("WHATSAPP_API_VERSION", "v22.0").strip()
    if not access_token or not phone_number_id:
        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:4096]},
    }
    result = _post_json(
        f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages",
        payload,
        {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    return bool(result)


def _get_sendpulse_access_token() -> str:
    cached_token = str(_sendpulse_token_cache.get("access_token") or "")
    expires_at = float(_sendpulse_token_cache.get("expires_at") or 0.0)
    now = time.time()
    if cached_token and expires_at > now + 30:
        return cached_token

    client_id = os.getenv("SENDPULSE_API_ID", "").strip()
    client_secret = os.getenv("SENDPULSE_API_SECRET", "").strip()
    if not client_id or not client_secret:
        return ""

    result = _post_json(
        "https://api.sendpulse.com/oauth/access_token",
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        {"Content-Type": "application/json"},
    )
    if not result:
        return ""

    access_token = str(result.get("access_token") or "").strip()
    expires_in = int(result.get("expires_in") or 3600)
    if not access_token:
        return ""

    _sendpulse_token_cache["access_token"] = access_token
    _sendpulse_token_cache["expires_at"] = now + max(expires_in - 60, 60)
    return access_token


def _send_sendpulse_whatsapp_text(bot_id: str, to: str, body: str) -> bool:
    access_token = _get_sendpulse_access_token()
    if not access_token or not bot_id or not to:
        return False

    result = _post_json(
        "https://api.sendpulse.com/whatsapp/contacts/sendByPhone",
        {
            "bot_id": bot_id,
            "phone": to,
            "message": {
                "type": "text",
                "text": {"body": body[:1024]},
            },
        },
        {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    return bool(result and result.get("success") is not False)


def _send_whatsapp_text(store: Store, provider_key: str, to: str, body: str) -> bool:
    provider = (store.whatsapp_provider or "meta").strip().lower()
    if provider == "sendpulse":
        return _send_sendpulse_whatsapp_text(store.whatsapp_bot_id or provider_key, to, body)
    return _send_meta_whatsapp_text(store.whatsapp_phone_number_id or provider_key, to, body)


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
    _send_whatsapp_text(store, provider_key, customer_id, result["reply"])
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


def _extract_sendpulse_message(payload: dict[str, Any]) -> tuple[str, str, str]:
    bot_id = (
        payload.get("bot_id")
        or payload.get("bot", {}).get("id")
        or payload.get("chatbot", {}).get("id")
        or ""
    )
    phone = (
        payload.get("phone")
        or payload.get("contact", {}).get("phone")
        or payload.get("subscriber", {}).get("phone")
        or payload.get("chat", {}).get("contact", {}).get("phone")
        or ""
    )
    message = payload.get("message")
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
        text_body = message or payload.get("text") or payload.get("body") or ""

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
        if isinstance(payload.get("entry"), list):
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
