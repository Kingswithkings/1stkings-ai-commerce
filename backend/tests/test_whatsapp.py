from app.routes.whatsapp import _extract_sendpulse_message, _find_store


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
