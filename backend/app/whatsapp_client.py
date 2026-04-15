import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from app.models import Store

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


def send_meta_whatsapp_text(phone_number_id: str, to: str, body: str) -> bool:
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    api_version = os.getenv("WHATSAPP_API_VERSION", "v22.0").strip()
    if not access_token or not phone_number_id or not to:
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


def send_sendpulse_whatsapp_text(bot_id: str, to: str, body: str) -> bool:
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


def send_store_whatsapp_text(store: Store, provider_key: str, to: str, body: str) -> bool:
    provider = (store.whatsapp_provider or "meta").strip().lower()
    if provider == "sendpulse":
        return send_sendpulse_whatsapp_text(store.whatsapp_bot_id or provider_key, to, body)
    return send_meta_whatsapp_text(store.whatsapp_phone_number_id or provider_key, to, body)
