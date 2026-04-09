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


def test_find_store_returns_store_from_provider_key():
    store = object()
    db = DummyDB(store)

    assert _find_store(db, provider_key="bot-42") is store
