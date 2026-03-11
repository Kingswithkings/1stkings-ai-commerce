from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from app.db import list_orders_by_store, get_order, update_order

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/orders")
def get_orders(store_slug: str = Query("naija-house")):
    return list_orders_by_store(store_slug)


class OrderStatusUpdate(BaseModel):
    status: str


@router.patch("/orders/{order_id}")
def update_order_status(order_id: int, payload: OrderStatusUpdate):
    allowed = {"confirmed", "accepted", "ready", "completed", "cancelled"}

    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")

    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_order(order_id, status=payload.status)
    return {"ok": True, "order_id": order_id, "status": payload.status}