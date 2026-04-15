from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    opening = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    order_notification_number = Column(String, nullable=True)
    whatsapp_enabled = Column(Boolean, nullable=False, default=False)
    whatsapp_provider = Column(String, nullable=False, default="meta")
    whatsapp_phone_number_id = Column(String, nullable=True)
    whatsapp_bot_id = Column(String, nullable=True)
    whatsapp_verify_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    admins = relationship("AdminUser", back_populates="store", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="admins")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_store_product_sku"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)

    sku = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    aliases = Column(Text, nullable=True)

    price = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="each")

    stock_qty = Column(Integer, nullable=False, default=0)
    in_stock = Column(Boolean, nullable=False, default=True)

    category = Column(String, nullable=True, default="Uncategorized")
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    size_pricing = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    min_stock_level = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship("Store", back_populates="products")
