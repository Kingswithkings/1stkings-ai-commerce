from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Store, Product
from app.size_pricing import loads_size_pricing

router = APIRouter()


@router.get("/products")
def list_products(store_slug: str = Query(...)):
    db: Session = SessionLocal()
    try:
        store = db.query(Store).filter(Store.slug == store_slug).first()
        if not store:
            raise HTTPException(status_code=404, detail=f"Unknown store: {store_slug}")

        products = (
            db.query(Product)
            .filter(Product.store_id == store.id, Product.is_active == True)
            .order_by(Product.name.asc())
            .all()
        )

        return [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "price": p.price,
                "unit": p.unit,
                "stock_qty": p.stock_qty,
                "in_stock": p.in_stock,
                "aliases": [a.strip() for a in (p.aliases or "").split(",") if a.strip()],
                "category": p.category or "Uncategorized",
                "image_url": p.image_url,
                "description": p.description,
                "size_pricing": loads_size_pricing(p.size_pricing),
                "is_active": p.is_active,
                "min_stock_level": p.min_stock_level,
                "low_stock": p.stock_qty <= p.min_stock_level if p.min_stock_level > 0 else False,
            }
            for p in products
        ]
    finally:
        db.close()
