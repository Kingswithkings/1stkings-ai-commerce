from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from app.db import log_message
from app.catalog import Catalog
from app.order_flow import handle_chat
from app.store_config import STORES

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    store_slug: str = "naija-house"


def get_catalog_for_store(store_slug: str) -> Catalog:
    store = STORES.get(store_slug)
    if not store:
        raise HTTPException(status_code=404, detail=f"Unknown store: {store_slug}")

    csv_path = Path(__file__).resolve().parents[2] / store["products_file"]
    return Catalog(csv_path=csv_path)


@router.post("/chat")
def chat(req: ChatRequest):
    catalog = get_catalog_for_store(req.store_slug)

    log_message(req.session_id, "user", req.message)
    result = handle_chat(req.session_id, req.message, catalog)
    log_message(req.session_id, "assistant", result["reply"])

    return result