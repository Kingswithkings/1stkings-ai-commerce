from app.db import Base, SessionLocal, engine
from app.models import Product, Store
from app.routes.whatsapp import _extract_sendpulse_message, _find_store, _reply_for_message


class DummyQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class DummyDB:
    def __init__(self, result):
        self.result = result

    def query(self, *args, **kwargs):
        return DummyQuery(self.result)


def test_extract_sendpulse_message_supports_nested_payload():
    bot_id, customer_phone, text_body = _extract_sendpulse_message(
        {
            "chatbot": {"id": "bot-42"},
            "subscriber": {"phone": "+2348000000000"},
            "message": {"text": {"body": "I need rice"}},
        }
    )

    assert bot_id == "bot-42"
    assert customer_phone == "+2348000000000"
    assert text_body == "I need rice"


def test_extract_sendpulse_message_supports_list_payload_with_contact_message():
    bot_id, customer_phone, text_body = _extract_sendpulse_message(
        [
            {
                "bot": {"id": "bot-99"},
                "contact": {
                    "phone": "+447700900001",
                    "last_message_data": {
                        "message": {
                            "text": {"body": "Do you have yam flour?"}
                        }
                    },
                },
            }
        ]
    )

    assert bot_id == "bot-99"
    assert customer_phone == "+447700900001"
    assert text_body == "Do you have yam flour?"


def test_extract_sendpulse_message_falls_back_to_contact_last_message():
    bot_id, customer_phone, text_body = _extract_sendpulse_message(
        {
            "bot_id": "bot-77",
            "contact": {
                "phone": "+447700900002",
                "last_message": "I need 2 bags of rice",
            },
        }
    )

    assert bot_id == "bot-77"
    assert customer_phone == "+447700900002"
    assert text_body == "I need 2 bags of rice"


def test_find_store_returns_store_from_provider_key():
    store = object()
    db = DummyDB(store)

    assert _find_store(db, provider_key="bot-42") is store


def test_whatsapp_checkout_confirms_to_customer_and_notifies_admin(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        store = Store(
            slug="test-store",
            name="Test Store",
            whatsapp_enabled=True,
            whatsapp_provider="sendpulse",
            whatsapp_bot_id="bot-42",
            whatsapp_number="+447700900101",
            order_notification_number="+447700900999",
        )
        db.add(store)
        db.flush()
        db.add(
            Product(
                store_id=store.id,
                sku="rice-1",
                name="Rice",
                aliases="bag of rice",
                price=4.5,
                unit="bag",
                stock_qty=10,
                in_stock=True,
                is_active=True,
                category="Groceries",
            )
        )
        db.commit()
        db.refresh(store)

        customer_messages: list[dict[str, str]] = []
        admin_messages: list[dict[str, str]] = []

        def fake_customer_send(store, provider_key, to, body):
            customer_messages.append(
                {
                    "provider_key": provider_key,
                    "to": to,
                    "body": body,
                }
            )
            return True

        def fake_admin_send(store, provider_key, to, body):
            admin_messages.append(
                {
                    "provider_key": provider_key,
                    "to": to,
                    "body": body,
                }
            )
            return True

        monkeypatch.setattr("app.routes.whatsapp.send_store_whatsapp_text", fake_customer_send)
        monkeypatch.setattr("app.order_notifications.send_store_whatsapp_text", fake_admin_send)

        customer_id = "+447700900123"

        _reply_for_message(db, store, customer_id, "rice", "bot-42")
        _reply_for_message(db, store, customer_id, "checkout", "bot-42")
        _reply_for_message(db, store, customer_id, "Jane Customer", "bot-42")
        _reply_for_message(db, store, customer_id, "pickup", "bot-42")
        _reply_for_message(db, store, customer_id, "Today 6pm", "bot-42")
        result = _reply_for_message(db, store, customer_id, "YES", "bot-42")

        assert result["to"] == customer_id
        assert "Order confirmed" in result["reply"]
        assert "Pickup: Today 6pm" in result["reply"]

        assert customer_messages[-1]["to"] == customer_id
        assert "Order confirmed" in customer_messages[-1]["body"]

        assert len(admin_messages) == 1
        assert admin_messages[0]["provider_key"] == "bot-42"
        assert admin_messages[0]["to"] == "+447700900999"
        assert "New order for Test Store" in admin_messages[0]["body"]
        assert "Jane Customer" in admin_messages[0]["body"]
        assert "Fulfillment: Pickup" in admin_messages[0]["body"]
    finally:
        db.close()
