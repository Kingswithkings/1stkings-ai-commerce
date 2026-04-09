import csv
import re
from dataclasses import dataclass
from pathlib import Path

from app.db import SessionLocal
from app.models import Product as DbProduct, Store

@dataclass
class Product:
    sku: str
    name: str
    aliases: list[str]
    price: float
    unit: str
    in_stock: int
    category: str  # ✅ NEW

def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _token_set(s: str) -> set[str]:
    return set(_norm(s).split())

def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

class Catalog:
    def __init__(self, csv_path: Path):
        self.products: list[Product] = []
        self._load(csv_path)

    def _load(self, csv_path: Path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                aliases = [a.strip() for a in (r.get("aliases") or "").split(",") if a.strip()]
                category = (r.get("category") or "").strip() or "Uncategorized"  # ✅ NEW

                self.products.append(
                    Product(
                        sku=r["sku"].strip(),
                        name=r["name"].strip(),
                        aliases=aliases,
                        price=float(r["price"]),
                        unit=(r.get("unit") or "").strip() or "unit",
                        in_stock=int(r.get("in_stock") or 0),
                        category=category,  # ✅ NEW
                    )
                )

    def match(self, query: str) -> tuple[Product | None, float, list[tuple[Product, float]]]:
        q = _token_set(query)
        scored: list[tuple[Product, float]] = []

        for p in self.products:
            candidates = [p.name] + p.aliases
            best = 0.0
            for c in candidates:
                best = max(best, jaccard(q, _token_set(c)))
            if best > 0:
                scored.append((p, best))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[0] if scored else (None, 0.0)
        return top[0], float(top[1]), scored[:5]


def load_catalog_for_store(store_slug: str) -> Catalog:
    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.slug == store_slug).first()
        if not store:
            raise ValueError(f"Unknown store: {store_slug}")

        products = (
            db.query(DbProduct)
            .filter(
                DbProduct.store_id == store.id,
                DbProduct.is_active == True,
                DbProduct.in_stock == True,
            )
            .order_by(DbProduct.name.asc())
            .all()
        )
    finally:
        db.close()

    catalog = Catalog.__new__(Catalog)
    catalog.products = [
        Product(
            sku=product.sku,
            name=product.name,
            aliases=[a.strip() for a in (product.aliases or "").split(",") if a.strip()],
            price=float(product.price),
            unit=product.unit or "unit",
            in_stock=int(product.stock_qty or 0),
            category=product.category or "Uncategorized",
        )
        for product in products
    ]
    return catalog
