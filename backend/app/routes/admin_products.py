from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AdminUser, Product, Store
from app.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/admin/products", tags=["admin-products"])
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    admin = db.query(AdminUser).filter(AdminUser.id == int(admin_id)).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    return admin


class ProductCreate(BaseModel):
    sku: str
    name: str
    aliases: str = ""
    price: float
    unit: str = "each"
    stock_qty: int = 0
    category: str = "Uncategorized"
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    min_stock_level: int = 0


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    aliases: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    stock_qty: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    min_stock_level: Optional[int] = None


class StockUpdate(BaseModel):
    stock_qty: int


class StatusUpdate(BaseModel):
    is_active: bool


class StoreChannelSettingsUpdate(BaseModel):
    whatsapp_enabled: bool
    whatsapp_provider: str = "meta"
    whatsapp_number: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_bot_id: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None


def _ensure_unique_store_channel_identifiers(
    db: Session,
    store_id: int,
    whatsapp_phone_number_id: str | None,
    whatsapp_bot_id: str | None,
) -> None:
    normalized_phone_number_id = (whatsapp_phone_number_id or "").strip() or None
    normalized_bot_id = (whatsapp_bot_id or "").strip() or None

    if normalized_phone_number_id:
        existing_phone_store = (
            db.query(Store)
            .filter(
                Store.id != store_id,
                Store.whatsapp_phone_number_id == normalized_phone_number_id,
            )
            .first()
        )
        if existing_phone_store:
            raise HTTPException(
                status_code=409,
                detail="This Meta phone number ID is already assigned to another store.",
            )

    if normalized_bot_id:
        existing_bot_store = (
            db.query(Store)
            .filter(
                Store.id != store_id,
                Store.whatsapp_bot_id == normalized_bot_id,
            )
            .first()
        )
        if existing_bot_store:
            raise HTTPException(
                status_code=409,
                detail="This SendPulse bot ID is already assigned to another store.",
            )


@router.get("")
def list_admin_products(
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    products = (
        db.query(Product)
        .filter(Product.store_id == admin.store_id)
        .order_by(Product.name.asc())
        .all()
    )

    return [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "aliases": p.aliases or "",
            "price": p.price,
            "unit": p.unit,
            "stock_qty": p.stock_qty,
            "in_stock": p.in_stock,
            "category": p.category or "Uncategorized",
            "image_url": p.image_url,
            "description": p.description,
            "is_active": p.is_active,
            "min_stock_level": p.min_stock_level,
            "low_stock": p.stock_qty <= p.min_stock_level if p.min_stock_level > 0 else False,
        }
        for p in products
    ]


@router.get("/settings")
def get_store_settings(
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == admin.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return {
        "store_slug": store.slug,
        "store_name": store.name,
        "whatsapp_enabled": bool(store.whatsapp_enabled),
        "whatsapp_provider": (store.whatsapp_provider or "meta"),
        "whatsapp_number": store.whatsapp_number or store.phone or "",
        "whatsapp_phone_number_id": store.whatsapp_phone_number_id or "",
        "whatsapp_bot_id": store.whatsapp_bot_id or "",
        "whatsapp_verify_token": store.whatsapp_verify_token or "",
    }


@router.patch("/settings")
def update_store_settings(
    payload: StoreChannelSettingsUpdate,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == admin.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    _ensure_unique_store_channel_identifiers(
        db=db,
        store_id=store.id,
        whatsapp_phone_number_id=payload.whatsapp_phone_number_id,
        whatsapp_bot_id=payload.whatsapp_bot_id,
    )

    store.whatsapp_enabled = payload.whatsapp_enabled
    store.whatsapp_provider = (payload.whatsapp_provider or "meta").strip() or "meta"
    store.whatsapp_number = (payload.whatsapp_number or "").strip() or None
    store.whatsapp_phone_number_id = (
        (payload.whatsapp_phone_number_id or "").strip() or None
    )
    store.whatsapp_bot_id = (payload.whatsapp_bot_id or "").strip() or None
    store.whatsapp_verify_token = (payload.whatsapp_verify_token or "").strip() or None

    db.commit()
    db.refresh(store)

    return {
        "message": "Store settings updated",
        "store": {
            "store_slug": store.slug,
            "store_name": store.name,
            "whatsapp_enabled": bool(store.whatsapp_enabled),
            "whatsapp_provider": store.whatsapp_provider or "meta",
            "whatsapp_number": store.whatsapp_number or "",
            "whatsapp_phone_number_id": store.whatsapp_phone_number_id or "",
            "whatsapp_bot_id": store.whatsapp_bot_id or "",
            "whatsapp_verify_token": store.whatsapp_verify_token or "",
        },
    }


@router.post("")
def create_product(
    payload: ProductCreate,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Product)
        .filter(Product.store_id == admin.store_id, Product.sku == payload.sku)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists for this store")

    product = Product(
        store_id=admin.store_id,
        sku=payload.sku.strip(),
        name=payload.name.strip(),
        aliases=payload.aliases.strip(),
        price=payload.price,
        unit=payload.unit.strip(),
        stock_qty=payload.stock_qty,
        in_stock=payload.stock_qty > 0,
        category=payload.category.strip() or "Uncategorized",
        image_url=(payload.image_url or "").strip() or None,
        description=(payload.description or "").strip() or None,
        is_active=payload.is_active,
        min_stock_level=payload.min_stock_level,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return {
        "message": "Product created",
        "product": {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "price": product.price,
            "unit": product.unit,
            "stock_qty": product.stock_qty,
            "in_stock": product.in_stock,
            "category": product.category,
            "image_url": product.image_url,
            "description": product.description,
            "is_active": product.is_active,
            "min_stock_level": product.min_stock_level,
        },
    }


@router.put("/{product_id}")
def update_product(
    product_id: int,
    payload: ProductUpdate,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.store_id == admin.store_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.sku is not None:
        product.sku = payload.sku.strip()
    if payload.name is not None:
        product.name = payload.name.strip()
    if payload.aliases is not None:
        product.aliases = payload.aliases.strip()
    if payload.price is not None:
        product.price = payload.price
    if payload.unit is not None:
        product.unit = payload.unit.strip()
    if payload.stock_qty is not None:
        product.stock_qty = payload.stock_qty
        product.in_stock = payload.stock_qty > 0
    if payload.category is not None:
        product.category = payload.category.strip() or "Uncategorized"
    if payload.image_url is not None:
        product.image_url = payload.image_url.strip() or None
    if payload.description is not None:
        product.description = payload.description.strip() or None
    if payload.is_active is not None:
        product.is_active = payload.is_active
    if payload.min_stock_level is not None:
        product.min_stock_level = payload.min_stock_level

    db.commit()
    db.refresh(product)

    return {
        "message": "Product updated",
        "product": {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "price": product.price,
            "unit": product.unit,
            "stock_qty": product.stock_qty,
            "in_stock": product.in_stock,
            "category": product.category,
            "image_url": product.image_url,
            "description": product.description,
            "is_active": product.is_active,
            "min_stock_level": product.min_stock_level,
        },
    }


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.store_id == admin.store_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"message": "Product deleted"}


@router.patch("/{product_id}/stock")
def update_stock(
    product_id: int,
    payload: StockUpdate,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.store_id == admin.store_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.stock_qty = payload.stock_qty
    product.in_stock = payload.stock_qty > 0

    db.commit()
    db.refresh(product)

    return {
        "message": "Stock updated",
        "product": {
            "id": product.id,
            "name": product.name,
            "stock_qty": product.stock_qty,
            "in_stock": product.in_stock,
        },
    }


@router.patch("/{product_id}/status")
def update_status(
    product_id: int,
    payload: StatusUpdate,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.store_id == admin.store_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = payload.is_active
    db.commit()
    db.refresh(product)

    return {
        "message": "Product status updated",
        "product": {
            "id": product.id,
            "name": product.name,
            "is_active": product.is_active,
        },
    }
