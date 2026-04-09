import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "store.db"

ALTERS = [
    "ALTER TABLE products ADD COLUMN image_url TEXT",
    "ALTER TABLE products ADD COLUMN description TEXT",
    "ALTER TABLE products ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
    "ALTER TABLE products ADD COLUMN min_stock_level INTEGER NOT NULL DEFAULT 0",
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for sql in ALTERS:
        try:
            cur.execute(sql)
            print(f"Ran: {sql}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Skipped existing column: {sql}")
            else:
                raise

    conn.commit()
    conn.close()
    print("Product table upgrade complete.")

if __name__ == "__main__":
    main()