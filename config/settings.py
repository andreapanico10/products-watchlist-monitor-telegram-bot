"""Configuration management using environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/amazon_affiliate_bot")
    
    # Amazon PA-API
    ENABLE_PA_API: bool = os.getenv("ENABLE_PA_API", "false").lower() in ("true", "1", "yes")
    AMAZON_ACCESS_KEY: str = os.getenv("AMAZON_ACCESS_KEY", "")
    AMAZON_SECRET_KEY: str = os.getenv("AMAZON_SECRET_KEY", "")
    AMAZON_ASSOCIATE_TAG: str = os.getenv("AMAZON_ASSOCIATE_TAG", "")
    AMAZON_REGION: str = os.getenv("AMAZON_REGION", "IT")
    
    # Affiliate
    AMAZON_AFFILIATE_TAG: str = os.getenv("AMAZON_AFFILIATE_TAG", "")
    
    # Scheduler
    PRICE_CHECK_INTERVAL_HOURS: int = int(os.getenv("PRICE_CHECK_INTERVAL_HOURS", "6"))
    DAILY_SUMMARY_HOUR: int = int(os.getenv("DAILY_SUMMARY_HOUR", "9"))  # Default: 9 AM
    DAILY_SUMMARY_MINUTE: int = int(os.getenv("DAILY_SUMMARY_MINUTE", "0"))


settings = Settings()
