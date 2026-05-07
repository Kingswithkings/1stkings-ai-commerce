import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import engine, ensure_schema
from app.models import Base
from app.routes.chat import router as chat_router
from app.routes.products import router as products_router
from app.routes.admin_auth import router as admin_auth_router
from app.routes.admin_products import router as admin_products_router
from app.routes.whatsapp import router as whatsapp_router
from app.uploads import UPLOADS_DIR, ensure_upload_directories
from app import llm

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("app.llm").setLevel(logging.DEBUG)

def create_app() -> FastAPI:
    settings = get_settings()

    Base.metadata.create_all(bind=engine)
    ensure_schema()
    ensure_upload_directories()

    app = FastAPI(title="1stkings AI Commerce API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/debug")
    def debug():
        return {
            "openai_enabled": bool(llm.OPENAI_API_KEY),
            "openai_model": llm.OPENAI_MODEL,
            "openai_api_url": llm.OPENAI_API_URL,
            "backend_env_loaded": True,
        }

    app.include_router(products_router)
    app.include_router(chat_router)
    app.include_router(admin_auth_router)
    app.include_router(admin_products_router)
    app.include_router(whatsapp_router)
    return app


app = create_app()
