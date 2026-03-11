import sqlite3
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "store.db"


def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def init_db():
    con = _conn()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        store_slug TEXT NOT NULL DEFAULT 'naija-house'
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        items TEXT NOT NULL,
        status TEXT NOT NULL,
        pickup_time TEXT,
        customer_name TEXT,
        customer_phone TEXT,
        flagged INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        store_slug TEXT NOT NULL DEFAULT 'naija-house'
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_state (
        session_id TEXT NOT NULL,
        store_slug TEXT NOT NULL DEFAULT 'naija-house',
        state TEXT NOT NULL,
        context TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (session_id, store_slug)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_store_slug ON messages(store_slug)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_store_slug ON orders(store_slug)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_state_store_slug ON user_state(store_slug)")

    con.commit()
    con.close()


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def log_message(session_id: str, role: str, text: str, store_slug: str = "naija-house"):
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO messages(session_id, role, text, created_at, store_slug) VALUES(?,?,?,?,?)",
        (session_id, role, text, now_iso(), store_slug)
    )
    con.commit()
    con.close()


def get_state(session_id: str, store_slug: str = "naija-house") -> tuple[str, dict]:
    con = _conn()
    cur = con.cursor()
    row = cur.execute(
        "SELECT state, context FROM user_state WHERE session_id=? AND store_slug=?",
        (session_id, store_slug)
    ).fetchone()
    con.close()
    if not row:
        return "browsing", {}
    return row["state"], json.loads(row["context"])


def set_state(session_id: str, state: str, context: dict, store_slug: str = "naija-house"):
    con = _conn()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO user_state(session_id, store_slug, state, context, updated_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(session_id, store_slug) DO UPDATE SET
            state=excluded.state,
            context=excluded.context,
            updated_at=excluded.updated_at
    """, (session_id, store_slug, state, json.dumps(context), now_iso()))

    con.commit()
    con.close()


def get_or_create_draft_order(session_id: str, store_slug: str = "naija-house") -> dict:
    con = _conn()
    cur = con.cursor()

    row = cur.execute("""
        SELECT * FROM orders
        WHERE session_id=? AND store_slug=? AND status IN ('draft','checkout')
        ORDER BY id DESC LIMIT 1
    """, (session_id, store_slug)).fetchone()

    if row:
        con.close()
        return dict(row)

    ts = now_iso()
    cur.execute("""
        INSERT INTO orders(session_id, items, status, created_at, updated_at, store_slug)
        VALUES(?,?,?,?,?,?)
    """, (session_id, json.dumps([]), "draft", ts, ts, store_slug))
    con.commit()

    order_id = cur.lastrowid
    row2 = cur.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    con.close()
    return dict(row2)


def update_order(order_id: int, **fields):
    if not fields:
        return

    con = _conn()
    cur = con.cursor()

    fields["updated_at"] = now_iso()
    cols = ", ".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values())
    vals.append(order_id)

    cur.execute(f"UPDATE orders SET {cols} WHERE id=?", vals)
    con.commit()
    con.close()


def get_order(order_id: int) -> dict | None:
    con = _conn()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def list_orders_by_store(store_slug: str) -> list[dict]:
    con = _conn()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT * FROM orders
        WHERE store_slug=?
        ORDER BY id DESC
    """, (store_slug,)).fetchall()
    con.close()
    return [dict(row) for row in rows]