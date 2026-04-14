import csv
from pathlib import Path

from app.db import SessionLocal, engine
from app.models import Base, Store, Product

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

STORE_FILES = {
    "naija-house": {
        "name": "Naija House",
        "phone": "07543494001",
        "opening": "Monday – Sunday",
        "file": DATA_DIR / "products_naija_house.csv",
    },
    "global-food-market": {
        "name": "Global Food Market",
        "phone": "+447587167843",
        "opening": "Monday – Sunday",
        "file": DATA_DIR / "products_global_food_market.csv",
    },
    "doncaster-budget-shop": {
        "name": "Doncaster Budget Shop",
        "phone": "+447345036753",
        "opening": "Monday – Sunday",
        "file": DATA_DIR / "products_najeebullah.csv",
    },
}


def normalize_stock_qty(value: str) -> int:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return 1
    if text in {"0", "false", "no"}:
        return 0
    return int(float(text))


def normalize_in_stock(stock_qty: int) -> bool:
    return stock_qty > 0


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        for slug, meta in STORE_FILES.items():
            csv_path = meta["file"]
            if not csv_path.exists():
                print(f"Skipping {slug}: missing file {csv_path}")
                continue

            store = db.query(Store).filter(Store.slug == slug).first()
            if not store:
                store = Store(
                    slug=slug,
                    name=meta["name"],
                    phone=meta["phone"],
                    opening=meta["opening"],
                )
                db.add(store)
                db.commit()
                db.refresh(store)
                print(f"Created store: {slug}")

            # Optional: clear existing products for fresh re-import
            db.query(Product).filter(Product.store_id == store.id).delete()
            db.commit()

            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    stock_qty = normalize_stock_qty(row.get("in_stock", "1"))

                    product = Product(
                        store_id=store.id,
                        sku=(row.get("sku") or "").strip(),
                        name=(row.get("name") or "").strip(),
                        aliases=(row.get("aliases") or "").strip(),
                        price=float(row.get("price") or 0),
                        unit=(row.get("unit") or "each").strip(),
                        stock_qty=stock_qty,
                        in_stock=normalize_in_stock(stock_qty),
                        category=(row.get("category") or "Uncategorized").strip(),
                        image_url=(row.get("image_url") or "").strip() or None,
                    )
                    db.add(product)

            db.commit()
            print(f"Imported products for {slug}")

        print("Done.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
