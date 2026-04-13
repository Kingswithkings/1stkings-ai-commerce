import json
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

DATABASE_URL = get_settings().database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_conn():
    with engine.begin() as conn:
        yield conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _column_names(table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})"))
        return {row[1] for row in rows}


def ensure_schema():
    with db_conn() as conn:
        existing_tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }

        if "orders" not in existing_tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        items TEXT NOT NULL DEFAULT '[]',
                        status TEXT NOT NULL DEFAULT 'draft',
                        pickup_time TEXT,
                        customer_name TEXT,
                        customer_phone TEXT,
                        flagged INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        store_slug TEXT NOT NULL DEFAULT 'naija-house',
                        channel TEXT NOT NULL DEFAULT 'web'
                    )
                    """
                ),
            )

        if "user_state" not in existing_tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE user_state (
                        session_id TEXT NOT NULL,
                        store_slug TEXT NOT NULL DEFAULT 'naija-house',
                        state TEXT NOT NULL,
                        context TEXT NOT NULL DEFAULT '{}',
                        updated_at TEXT NOT NULL,
                        channel TEXT NOT NULL DEFAULT 'web',
                        PRIMARY KEY (session_id, store_slug, channel)
                    )
                    """
                ),
            )

        if "messages" not in existing_tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        text TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        store_slug TEXT NOT NULL DEFAULT 'naija-house',
                        channel TEXT NOT NULL DEFAULT 'web'
                    )
                    """
                ),
            )

        store_columns = _column_names("stores") if "stores" in existing_tables else set()
        if "whatsapp_number" not in store_columns:
            conn.execute(text("ALTER TABLE stores ADD COLUMN whatsapp_number VARCHAR"))
        if "whatsapp_enabled" not in store_columns:
            conn.execute(
                text(
                    "ALTER TABLE stores ADD COLUMN whatsapp_enabled BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        if "whatsapp_provider" not in store_columns:
            conn.execute(
                text(
                    "ALTER TABLE stores ADD COLUMN whatsapp_provider VARCHAR NOT NULL DEFAULT 'meta'"
                )
            )
        if "whatsapp_phone_number_id" not in store_columns:
            conn.execute(
                text("ALTER TABLE stores ADD COLUMN whatsapp_phone_number_id VARCHAR")
            )
        if "whatsapp_bot_id" not in store_columns:
            conn.execute(text("ALTER TABLE stores ADD COLUMN whatsapp_bot_id VARCHAR"))
        if "whatsapp_verify_token" not in store_columns:
            conn.execute(text("ALTER TABLE stores ADD COLUMN whatsapp_verify_token VARCHAR"))

        product_columns = _column_names("products") if "products" in existing_tables else set()
        if "size_pricing" not in product_columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN size_pricing TEXT"))

        order_columns = _column_names("orders")
        if "channel" not in order_columns:
            conn.execute(
                text("ALTER TABLE orders ADD COLUMN channel TEXT NOT NULL DEFAULT 'web'")
            )

        state_columns = _column_names("user_state")
        if "channel" not in state_columns:
            conn.execute(
                text("ALTER TABLE user_state ADD COLUMN channel TEXT NOT NULL DEFAULT 'web'")
            )

        message_columns = _column_names("messages")
        if "channel" not in message_columns:
            conn.execute(
                text("ALTER TABLE messages ADD COLUMN channel TEXT NOT NULL DEFAULT 'web'")
            )

        conn.execute(
            text(
                "UPDATE stores SET whatsapp_number = phone WHERE whatsapp_number IS NULL"
            )
        )
        conn.execute(
            text(
                """
                UPDATE stores
                SET whatsapp_enabled = 1
                WHERE COALESCE(TRIM(whatsapp_number), '') <> ''
                """
            )
        )


def get_order(order_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM orders WHERE id = :order_id"),
            {"order_id": order_id},
        ).mappings().first()
        return dict(row) if row else None


def get_or_create_draft_order(
    session_id: str,
    store_slug: str,
    channel: str = "web",
) -> dict:
    with db_conn() as conn:
        row = conn.execute(
            text(
                """
                SELECT * FROM orders
                WHERE session_id = :session_id
                  AND store_slug = :store_slug
                  AND channel = :channel
                  AND status IN ('draft', 'checkout')
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {
                "session_id": session_id,
                "store_slug": store_slug,
                "channel": channel,
            },
        ).mappings().first()

        if row:
            return dict(row)

        now = _now()
        conn.execute(
            text(
                """
                INSERT INTO orders (
                    session_id, items, status, pickup_time, customer_name,
                    customer_phone, flagged, created_at, updated_at, store_slug, channel
                ) VALUES (
                    :session_id, '[]', 'draft', NULL, NULL,
                    NULL, 0, :created_at, :updated_at, :store_slug, :channel
                )
                """
            ),
            {
                "session_id": session_id,
                "created_at": now,
                "updated_at": now,
                "store_slug": store_slug,
                "channel": channel,
            },
        )

        created = conn.execute(
            text(
                """
                SELECT * FROM orders
                WHERE session_id = :session_id
                  AND store_slug = :store_slug
                  AND channel = :channel
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {
                "session_id": session_id,
                "store_slug": store_slug,
                "channel": channel,
            },
        ).mappings().first()

        return dict(created)


def update_order(order_id: int, **fields) -> dict | None:
    if not fields:
        return get_order(order_id)

    allowed = {
        "items",
        "status",
        "pickup_time",
        "customer_name",
        "customer_phone",
        "flagged",
        "channel",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return get_order(order_id)

    updates["updated_at"] = _now()
    set_parts = [f"{key} = :{key}" for key in updates]
    updates["order_id"] = order_id

    with db_conn() as conn:
        conn.execute(
            text(
                f"UPDATE orders SET {', '.join(set_parts)} WHERE id = :order_id"
            ),
            updates,
        )

    return get_order(order_id)


def get_state(session_id: str, store_slug: str, channel: str = "web") -> tuple[str, dict]:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT state, context
                FROM user_state
                WHERE session_id = :session_id
                  AND store_slug = :store_slug
                  AND channel = :channel
                """
            ),
            {
                "session_id": session_id,
                "store_slug": store_slug,
                "channel": channel,
            },
        ).first()

    if not row:
        return "browsing", {}

    try:
        ctx = json.loads(row[1] or "{}")
    except json.JSONDecodeError:
        ctx = {}
    return row[0], ctx


def set_state(session_id: str, state: str, context: dict, store_slug: str, channel: str = "web"):
    payload = json.dumps(context or {})
    now = _now()
    with db_conn() as conn:
        existing = conn.execute(
            text(
                """
                SELECT 1
                FROM user_state
                WHERE session_id = :session_id
                  AND store_slug = :store_slug
                  AND channel = :channel
                """
            ),
            {
                "session_id": session_id,
                "store_slug": store_slug,
                "channel": channel,
            },
        ).first()

        if existing:
            conn.execute(
                text(
                    """
                    UPDATE user_state
                    SET state = :state, context = :context, updated_at = :updated_at
                    WHERE session_id = :session_id
                      AND store_slug = :store_slug
                      AND channel = :channel
                    """
                ),
                {
                    "session_id": session_id,
                    "store_slug": store_slug,
                    "channel": channel,
                    "state": state,
                    "context": payload,
                    "updated_at": now,
                },
            )
            return

        conn.execute(
            text(
                """
                INSERT INTO user_state (
                    session_id, store_slug, state, context, updated_at, channel
                ) VALUES (
                    :session_id, :store_slug, :state, :context, :updated_at, :channel
                )
                """
            ),
            {
                "session_id": session_id,
                "store_slug": store_slug,
                "channel": channel,
                "state": state,
                "context": payload,
                "updated_at": now,
            },
        )


def log_message(
    session_id: str,
    role: str,
    message_text: str,
    store_slug: str,
    channel: str = "web",
):
    with db_conn() as conn:
        conn.execute(
            text(
                """
                INSERT INTO messages (
                    session_id, role, text, created_at, store_slug, channel
                ) VALUES (
                    :session_id, :role, :text, :created_at, :store_slug, :channel
                )
                """
            ),
            {
                "session_id": session_id,
                "role": role,
                "text": message_text,
                "created_at": _now(),
                "store_slug": store_slug,
                "channel": channel,
            },
        )


def list_orders_by_store(store_slug: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT *
                FROM orders
                WHERE store_slug = :store_slug
                ORDER BY updated_at DESC, id DESC
                """
            ),
            {"store_slug": store_slug},
        ).mappings().all()
        return [dict(row) for row in rows]
