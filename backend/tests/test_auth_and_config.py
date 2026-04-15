import io
import json

from fastapi.testclient import TestClient

from app.db import SessionLocal, Base, engine, get_or_create_draft_order, set_state, update_order
from app.main import app
from app.models import AdminUser, Product, Store
from app.order_flow import handle_chat
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


def test_store_settings_include_order_notification_number():
    client = TestClient(app)
    login = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]

    update_response = client.patch(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "whatsapp_enabled": True,
            "whatsapp_provider": "sendpulse",
            "whatsapp_number": "+447700900101",
            "order_notification_number": "+447700900999",
            "whatsapp_phone_number_id": "",
            "whatsapp_bot_id": "bot-101",
            "whatsapp_verify_token": "",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["store"]["order_notification_number"] == "+447700900999"

    get_response = client.get(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["order_notification_number"] == "+447700900999"


def test_store_settings_allow_blank_order_notification_number():
    client = TestClient(app)
    login = client.post(
        "/admin/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]

    update_response = client.patch(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "whatsapp_enabled": True,
            "whatsapp_provider": "sendpulse",
            "whatsapp_number": "+447700900101",
            "order_notification_number": "",
            "whatsapp_phone_number_id": "",
            "whatsapp_bot_id": "bot-101",
            "whatsapp_verify_token": "",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["store"]["order_notification_number"] == ""

    get_response = client.get(
        "/admin/products/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["order_notification_number"] == ""


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


def test_confirmed_order_sends_notification_to_store_recipient(monkeypatch):
    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.slug == "test-store").first()
        assert store is not None
        store.whatsapp_enabled = True
        store.whatsapp_provider = "sendpulse"
        store.whatsapp_bot_id = "bot-abc"
        store.order_notification_number = "+447700900999"
        db.commit()
    finally:
        db.close()

    order = get_or_create_draft_order("notify-session", "test-store", "web")
    update_order(
        int(order["id"]),
        items=json.dumps(
            [
                {
                    "sku": "rice-1",
                    "name": "Rice",
                    "qty": 2,
                    "unit_price": 4.5,
                }
            ]
        ),
        status="checkout",
        fulfillment_type="pickup",
        pickup_time="Today 6pm",
        customer_name="Jane Customer",
        customer_phone="+447700900123",
    )
    set_state("notify-session", "checkout_confirm", {"order_id": order["id"]}, "test-store", "web")

    sent_payload: dict[str, str] = {}

    def fake_send(store, provider_key, to, body):
        sent_payload["provider_key"] = provider_key
        sent_payload["to"] = to
        sent_payload["body"] = body
        return True

    monkeypatch.setattr("app.order_notifications.send_store_whatsapp_text", fake_send)

    result = handle_chat(
        session_id="notify-session",
        user_text="YES",
        catalog=None,
        store_slug="test-store",
        channel="web",
    )

    assert result["cart"]["status"] == "confirmed"
    assert sent_payload["provider_key"] == "bot-abc"
    assert sent_payload["to"] == "+447700900999"
    assert "New order for Test Store" in sent_payload["body"]
    assert "Order #" in sent_payload["body"]
    assert "Jane Customer" in sent_payload["body"]
    assert "Rice" in sent_payload["body"]
    assert "Fulfillment: Pickup" in sent_payload["body"]


def test_checkout_asks_delivery_or_pickup_after_customer_info():
    order = get_or_create_draft_order("web-checkout-session", "test-store", "web")
    update_order(
        int(order["id"]),
        items=json.dumps(
            [
                {
                    "sku": "rice-1",
                    "name": "Rice",
                    "qty": 1,
                    "unit_price": 4.5,
                }
            ]
        ),
    )

    result = handle_chat(
        session_id="web-checkout-session",
        user_text="checkout",
        catalog=None,
        store_slug="test-store",
        channel="web",
    )
    assert "What’s your name?" in result["reply"]

    result = handle_chat(
        session_id="web-checkout-session",
        user_text="Jane Customer",
        catalog=None,
        store_slug="test-store",
        channel="web",
    )
    assert "What phone number" in result["reply"]

    result = handle_chat(
        session_id="web-checkout-session",
        user_text="+447700900123",
        catalog=None,
        store_slug="test-store",
        channel="web",
    )
    assert "delivery or pickup" in result["reply"].lower()

    result = handle_chat(
        session_id="web-checkout-session",
        user_text="delivery",
        catalog=None,
        store_slug="test-store",
        channel="web",
    )
    assert "delivery address" in result["reply"].lower()

    result = handle_chat(
        session_id="web-checkout-session",
        user_text="10 Downing Street",
        catalog=None,
        store_slug="test-store",
        channel="web",
    )
    assert "Confirm your order" in result["reply"]
    assert "Delivery: 10 Downing Street" in result["reply"]


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
