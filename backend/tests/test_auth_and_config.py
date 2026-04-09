from fastapi.testclient import TestClient

from app.db import SessionLocal, Base, engine
from app.main import app
from app.models import AdminUser, Store
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
