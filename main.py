"""Main entry point for the Amazon Affiliate Bot."""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application
from config.settings import settings
from bot.handlers import register_handlers
from scheduler.price_checker import check_prices_job

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to start bot and scheduler."""
    # Validate configuration
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
    
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL not set in environment variables")
    
    logger.info("Starting Amazon Affiliate Bot...")
    
    # Create Telegram application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    register_handlers(application)
    
    # Create bot instance for scheduler
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    # Setup scheduler
    scheduler = AsyncIOScheduler()
    
    # Add price check job
    interval_hours = settings.PRICE_CHECK_INTERVAL_HOURS
    scheduler.add_job(
        check_prices_job,
        'interval',
        hours=interval_hours,
        args=[bot],
        id='price_check',
        replace_existing=True
    )
    
    logger.info(f"Price check job scheduled to run every {interval_hours} hours")
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")
    
    # Initialize database tables (if needed)
    try:
        from database.database import engine, Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.warning(f"Could not initialize database tables: {e}")
        logger.warning("Make sure to run 'alembic upgrade head' to create tables")
    
    # Start bot
    logger.info("Bot is running. Press Ctrl+C to stop.")
    await application.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

