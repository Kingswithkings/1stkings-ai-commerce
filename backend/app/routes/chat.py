from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.catalog import load_catalog_for_store
from app.db import SessionLocal, log_message
from app.models import Store
from app.order_flow import handle_chat

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    store_slug: str = "naija-house"


@router.post("/chat")
def chat(payload: ChatRequest):
    try:
        catalog = load_catalog_for_store(payload.store_slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_message(payload.session_id, "user", payload.message, payload.store_slug, "web")
    result = handle_chat(
        session_id=payload.session_id,
        user_text=payload.message,
        catalog=catalog,
        store_slug=payload.store_slug,
        channel="web",
    )
    log_message(payload.session_id, "assistant", result["reply"], payload.store_slug, "web")
    return result


@router.get("/stores/{store_slug}/channel-config")
def store_channel_config(store_slug: str):
    db: Session = SessionLocal()
    try:
        store = db.query(Store).filter(Store.slug == store_slug).first()
        if not store:
            raise HTTPException(status_code=404, detail=f"Unknown store: {store_slug}")

        whatsapp_number = (store.whatsapp_number or store.phone or "").strip()
        whatsapp_link = ""
        if whatsapp_number:
            normalized = "".join(ch for ch in whatsapp_number if ch.isdigit())
            whatsapp_link = f"https://wa.me/{normalized}" if normalized else ""

        return {
            "store_slug": store.slug,
            "store_name": store.name,
            "phone": store.phone,
            "whatsapp": {
                "enabled": bool(store.whatsapp_enabled),
                "number": whatsapp_number or None,
                "link": whatsapp_link or None,
            },
        }
    finally:
        db.close()
