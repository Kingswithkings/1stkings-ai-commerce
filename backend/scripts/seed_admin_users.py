from app.db import SessionLocal
from app.models import Store, AdminUser
from app.security import hash_password

SEED_ADMINS = [
    {
        "store_slug": "doncaster-budget-shop",
        "name": "Doncaster Budget Shop Owner",
        "email": "owner@doncasterbudgetshop.com",
        "password": "Admin123!",
    },
    {
        "store_slug": "naija-house",
        "name": "Naija House Owner",
        "email": "owner@naijahouse.com",
        "password": "Admin123!",
    },
    {
        "store_slug": "global-food-market",
        "name": "Global Food Market Owner",
        "email": "owner@globalfood.com",
        "password": "Admin123!",
    },
]


def main():
    db = SessionLocal()
    try:
        for item in SEED_ADMINS:
            store = db.query(Store).filter(Store.slug == item["store_slug"]).first()
            if not store:
                print(f"Store not found: {item['store_slug']}")
                continue

            existing = db.query(AdminUser).filter(AdminUser.email == item["email"]).first()
            if existing:
                print(f"Admin already exists: {item['email']}")
                continue

            admin = AdminUser(
                store_id=store.id,
                name=item["name"],
                email=item["email"],
                password_hash=hash_password(item["password"]),
            )
            db.add(admin)
            db.commit()

            print(f"Created admin: {item['email']} for {item['store_slug']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
