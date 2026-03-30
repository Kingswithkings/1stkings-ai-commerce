from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from app.catalog import Catalog
from app.store_config import STORES

router = APIRouter()


def get_catalog_for_store(store_slug: str) -> Catalog:
    store = STORES.get(store_slug)
    if not store:
        raise HTTPException(status_code=404, detail=f"Unknown store: {store_slug}")

    csv_path = Path(__file__).resolve().parents[2] / store["products_file"]

    if not csv_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"CSV file not found for store '{store_slug}': {csv_path}"
        )

    try:
        return Catalog(csv_path=csv_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load catalog for store '{store_slug}': {str(e)}"
        )


@router.get("/products")
def list_products(store_slug: str = Query("naija-house")):
    catalog = get_catalog_for_store(store_slug)

    return [
        {
            "sku": p.sku,
            "name": p.name,
            "price": p.price,
            "unit": p.unit,
            "in_stock": p.in_stock,
            "aliases": p.aliases,
            "category": getattr(p, "category", None) or "Uncategorized",
        }
        for p in catalog.products
    ]