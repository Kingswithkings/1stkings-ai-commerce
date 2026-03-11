from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routes.chat import router as chat_router
from app.routes.products import router as products_router
from app.routes.admin import router as admin_router

app = FastAPI(title="1stkings AI Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://global-food-webbot-cdaf.vercel.app",
        "https://naija-house-webbotapp.vercel.app",
        "https://naija-house-webbot.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(chat_router)
app.include_router(admin_router)

init_db()