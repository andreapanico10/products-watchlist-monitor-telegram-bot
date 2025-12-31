"""SQLAlchemy models for the database."""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base


class User(Base):
    """User model for Telegram users."""
    __tablename__ = "users"
    
    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language_code = Column(String, nullable=True)  # e.g., "it", "en"
    is_bot = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, nullable=True)  # Telegram Premium
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Referral system fields
    referrer_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True, index=True)
    is_vip = Column(Boolean, default=False, nullable=False)
    referral_count = Column(Integer, default=0, nullable=False)
    product_limit = Column(Integer, default=3, nullable=False)
    
    # Relationships
    user_products = relationship("UserProduct", back_populates="user", cascade="all, delete-orphan")
    referrer = relationship("User", remote_side=[telegram_id], foreign_keys=[referrer_id])


class Product(Base):
    """Product model for Amazon products."""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)  # Product URL
    initial_price = Column(Float, nullable=True)  # Nullable se PA-API non è abilitata
    target_price = Column(Float, nullable=True)
    affiliate_code = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user_products = relationship("UserProduct", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")


class UserProduct(Base):
    """Junction table for users and products (watchlist)."""
    __tablename__ = "user_products"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_products")
    product = relationship("Product", back_populates="user_products")


class PriceHistory(Base):
    """Price history for products."""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="EUR")
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="price_history")
