import io

from fastapi.testclient import TestClient

from app.db import SessionLocal, Base, engine
from app.main import app
from app.models import AdminUser, Product, Store
from app.security import hash_password


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        primary_store = Store(slug="test-store", name="Test Store", phone="+123")
        secondary_store = Store(slug="second-store", name="Second Store", phone="+456")
        db.add_all([primary_store, secondary_store])
        db.flush()
        db.add_all(
            [
                AdminUser(
                    store_id=primary_store.id,
                    name="Owner",
                    email="owner@example.com",
                    password_hash=hash_password("secret123"),
                ),
                AdminUser(
                    store_id=secondary_store.id,
                    name="Second Owner",
                    email="second@example.com",
                    password_hash=hash_password("secret123"),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_admin_login_returns_bearer_token():
    client = TestClient(app)
    response = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["store_slug"] == "test-store"
    assert body["admin_name"] == "Owner"
    assert body["access_token"]


def test_store_settings_reject_duplicate_sendpulse_bot_id():
    client = TestClient(app)
    first_login = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    second_login = client.post(
        "/admin/login",
        json={"email": "second@example.com", "password": "secret123"},
    )
    first_token = first_login.json()["access_token"]
    second_token = second_login.json()["access_token"]

    first_update = client.patch(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {first_token}"},
        json={
            "whatsapp_enabled": True,
            "whatsapp_provider": "sendpulse",
            "whatsapp_number": "+447700900001",
            "whatsapp_phone_number_id": "",
            "whatsapp_bot_id": "447311852882",
            "whatsapp_verify_token": "",
        },
    )
    duplicate_update = client.patch(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {second_token}"},
        json={
            "whatsapp_enabled": True,
            "whatsapp_provider": "sendpulse",
            "whatsapp_number": "+447700900002",
            "whatsapp_phone_number_id": "",
            "whatsapp_bot_id": "447311852882",
            "whatsapp_verify_token": "",
        },
    )

    assert first_update.status_code == 200
    assert duplicate_update.status_code == 409
    assert "already assigned" in duplicate_update.json()["detail"]


def test_store_settings_reject_duplicate_meta_phone_number_id():
    client = TestClient(app)
    first_login = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    second_login = client.post(
        "/admin/login",
        json={"email": "second@example.com", "password": "secret123"},
    )
    first_token = first_login.json()["access_token"]
    second_token = second_login.json()["access_token"]

    first_update = client.patch(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {first_token}"},
        json={
            "whatsapp_enabled": True,
            "whatsapp_provider": "meta",
            "whatsapp_number": "+447700900001",
            "whatsapp_phone_number_id": "meta-phone-1",
            "whatsapp_bot_id": "",
            "whatsapp_verify_token": "verify-1",
        },
    )
    duplicate_update = client.patch(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {second_token}"},
        json={
            "whatsapp_enabled": True,
            "whatsapp_provider": "meta",
            "whatsapp_number": "+447700900002",
            "whatsapp_phone_number_id": "meta-phone-1",
            "whatsapp_bot_id": "",
            "whatsapp_verify_token": "verify-2",
        },
    )

    assert first_update.status_code == 200
    assert duplicate_update.status_code == 409
    assert "already assigned" in duplicate_update.json()["detail"]


def test_admin_can_create_product_with_uploaded_image():
    client = TestClient(app)
    login = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/admin/products",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "sku": "plantain-1",
            "name": "Plantain",
            "aliases": "ripe plantain",
            "price": "3.5",
            "unit": "each",
            "stock_qty": "8",
            "category": "Fruit",
            "image_url": "",
            "description": "Fresh plantain",
            "is_active": "true",
            "min_stock_level": "2",
            "remove_image": "false",
        },
        files={"image_file": ("plantain.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product"]["image_url"].startswith("/uploads/products/store-")

    uploaded_image = client.get(body["product"]["image_url"])
    assert uploaded_image.status_code == 200
    assert uploaded_image.content == b"fake-image-bytes"

    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.sku == "plantain-1").first()
        assert product is not None
        assert product.image_url == body["product"]["image_url"]
    finally:
        db.close()


def test_admin_can_create_product_with_size_pricing():
    client = TestClient(app)
    login = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/admin/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sku": "drink-1",
            "name": "Malt Drink",
            "aliases": "malt",
            "price": 1.5,
            "unit": "bottle",
            "stock_qty": 12,
            "category": "Drinks",
            "image_url": None,
            "description": "Chilled drink",
            "size_pricing": [
                {"label": "330ml", "price": 1.5},
                {"label": "1L", "price": 2.9},
            ],
            "is_active": True,
            "min_stock_level": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product"]["size_pricing"] == [
        {"label": "330ml", "price": 1.5},
        {"label": "1L", "price": 2.9},
    ]
