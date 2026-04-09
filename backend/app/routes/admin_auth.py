from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AdminUser, Store
from app.schemas_auth import LoginRequest, LoginResponse
from app.security import verify_password, create_access_token

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login", response_model=LoginResponse)
def admin_login(payload: LoginRequest):
    db: Session = SessionLocal()
    try:
        admin = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(payload.password, admin.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        store = db.query(Store).filter(Store.id == admin.store_id).first()
        if not store:
            raise HTTPException(status_code=500, detail="Admin store not found")

        token = create_access_token(
            {
                "sub": str(admin.id),
                "email": admin.email,
                "store_id": store.id,
                "store_slug": store.slug,
            }
        )

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            store_slug=store.slug,
            store_name=store.name,
            admin_name=admin.name,
        )
    finally:
        db.close()