"""Main entry point for the Amazon Affiliate Bot."""
import asyncio
import logging
import nest_asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application
from config.settings import settings
from bot.handlers import register_handlers
from scheduler.price_checker import check_prices_job, daily_summary_job

# Allow nested event loops (needed for APScheduler + python-telegram-bot)
nest_asyncio.apply()

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
    
    # Add error handler for network errors (reduce log noise)
    async def error_handler(update: object, context) -> None:
        """Handle errors silently for network issues."""
        error = context.error
        if isinstance(error, Exception):
            error_name = error.__class__.__name__
            # Only log non-network errors or critical ones
            if "NetworkError" not in error_name and "RemoteProtocolError" not in str(error):
                logger.error(f"Exception while handling an update: {error}", exc_info=error)
    
    application.add_error_handler(error_handler)
    
    # Create bot instance for scheduler and command registration
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    # Register bot commands (so they appear when user types "/")
    try:
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Avvia il bot e vedi le istruzioni"),
            BotCommand("watchlist", "Visualizza i tuoi prodotti monitorati"),
            BotCommand("remove", "Rimuovi un prodotto dalla watchlist (usa: /remove ASIN)"),
        ]
        await bot.set_my_commands(commands)
        logger.info("Bot commands registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register bot commands: {e}")
    
    # Setup scheduler - will use the current event loop
    scheduler = AsyncIOScheduler()
    
    # Price check job: runs every minute, uses PA-API or scraping based on configuration
    scheduler.add_job(
        check_prices_job,
        'interval',
        minutes=1,
        args=[bot],
        id='price_check',
        replace_existing=True
    )
    method = "PA-API" if settings.ENABLE_PA_API else "Web Scraping"
    logger.info(f"Price check job scheduled to run every 1 minute using {method}")
    
    # Daily summary job: optional, runs at configured time
    summary_hour = settings.DAILY_SUMMARY_HOUR
    summary_minute = settings.DAILY_SUMMARY_MINUTE
    scheduler.add_job(
        daily_summary_job,
        'cron',
        hour=summary_hour,
        minute=summary_minute,
        args=[bot],
        id='daily_summary',
        replace_existing=True
    )
    logger.info(f"Daily summary job scheduled to run at {summary_hour:02d}:{summary_minute:02d}")
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")
    
    # Initialize database tables (if needed)
    # Wait a bit for database to be ready
    import time
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            from database.database import engine, Base
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized")
            break
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Could not connect to database (attempt {retry_count}/{max_retries}): {e}")
                logger.info("Retrying in 3 seconds...")
                time.sleep(3)
            else:
                logger.error(f"Could not initialize database tables after {max_retries} attempts: {e}")
                logger.error("Make sure the database is running and accessible")
    
    # Start bot
    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        # Use run_polling with stop_signals=None to avoid event loop conflicts
        await application.run_polling(stop_signals=None, close_loop=False, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        logger.info("Shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

