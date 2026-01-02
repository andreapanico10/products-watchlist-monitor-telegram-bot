"""Price checker scheduler job."""
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import Product, UserProduct, PriceHistory
from amazon.api_client import AmazonAPIClient
from amazon.scraper import AmazonScraper
from amazon.affiliate import generate_affiliate_link
from bot.messages import get_price_drop_notification, get_daily_summary_message, get_channel_deal_message
from telegram import Bot
from config.settings import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# Global index for product rotation
_product_index = 0


async def check_single_product(bot: Bot, product: Product, price_fetcher, method: str, db: Session, bot_username: str = None):
    """
    Check a single product and update price history.
    
    Args:
        bot: Telegram Bot instance
        product: Product to check
        price_fetcher: Price fetcher instance (API or Scraper)
        method: Method name for logging
        db: Database session
        bot_username: Bot username for referral links in messages
    """
    try:
        # Get current price using selected method
        product_info = price_fetcher.get_product_info(product.asin)
        
        if not product_info:
            logger.warning(f"[{product.asin}] Could not get product info using {method}. Page might be blocked or ASIN is invalid.")
            return
            
        if product_info.get('price') is None:
            logger.warning(f"[{product.asin}] Product info retrieved but price is missing using {method}.")
            return
        
        current_price = product_info['price']
        currency = product_info.get('currency', 'EUR')
        
        # Update product title if we got a better one
        if product_info.get('title') and not product.title:
            product.title = product_info['title']
        
        # Update product URL if not set
        if product_info.get('url') and not product.url:
            product.url = product_info['url']
            
        # Get PREVIOUS price record (before adding new one) to check for drops
        previous_price_record = db.query(PriceHistory).filter(
            PriceHistory.product_id == product.id
        ).order_by(PriceHistory.checked_at.desc()).first()
        
        previous_price = previous_price_record.price if previous_price_record else None
        
        logger.info(f"[{product.asin}] Price check: previous={previous_price}, current={current_price}, initial={product.initial_price}, target={product.target_price}")
        
        # Update price to history (update existing or create if first time)
        from sqlalchemy.sql import func
        if previous_price_record:
            previous_price_record.price = current_price
            previous_price_record.currency = currency
            previous_price_record.checked_at = func.now()
            logger.debug(f"[{product.asin}] Updated existing price history record")
        else:
            price_history = PriceHistory(
                product_id=product.id,
                price=current_price,
                currency=currency
            )
            db.add(price_history)
            logger.info(f"[{product.asin}] Created first price history record")
        
        db.commit() # Commit changes to ensure previous_price_record is updated        
        # Update initial_price if not set
        if not product.initial_price:
            product.initial_price = current_price
            logger.info(f"[{product.asin}] Set initial_price to {current_price}")
        
        # Check if price dropped
        price_dropped = False
        comparison_price = None
        
        # Logic to detect drop:
        # 1. precise drop via previous_price (prevents spam)
        # 2. meets target/initial criteria
        
        if previous_price:
            if current_price < previous_price:
                logger.info(f"[{product.asin}] Price dropped: {previous_price} → {current_price}")
                # It dropped since last check
                if (product.target_price and current_price < product.target_price) or \
                   (product.initial_price and current_price < product.initial_price):
                    price_dropped = True
                    comparison_price = previous_price
                    logger.info(f"[{product.asin}] ✅ PRICE DROP DETECTED! Will notify users.")
                else:
                    logger.info(f"[{product.asin}] ❌ Price dropped but not below target/initial. No notification.")
            else:
                logger.debug(f"[{product.asin}] Price stable or increased: {previous_price} → {current_price}")
        else:
            logger.info(f"[{product.asin}] First price check (no previous price)")
            # First check ever
            if (product.target_price and current_price < product.target_price):
                price_dropped = True
                comparison_price = product.initial_price
                logger.info(f"[{product.asin}] ✅ Below target on first check. Will notify.")
            # Note: We don't notify drop < initial_price on first check if no target set,
            # because initial_price is usually just set to current_price.
        
        # --- CHANNEL BROADCASTING LOGIC ---
        # Broadcast if:
        # 1. Channel ID is set
        # 2. Price dropped relative to previous check (to avoid spam)
        # 3. Discount >= Threshold (vs Initial Price)
        
        if settings.TELEGRAM_CHANNEL_ID and previous_price and current_price < previous_price:
            reference_price = product.initial_price or previous_price
            if reference_price > 0:
                discount_percent = ((reference_price - current_price) / reference_price) * 100
                
                if discount_percent >= settings.CHANNEL_DEAL_THRESHOLD:
                    try:
                        channel_msg = get_channel_deal_message(
                            {
                                'title': product.title or 'Prodotto',
                                'asin': product.asin
                            },
                            reference_price,
                            current_price,
                            currency,
                            generate_affiliate_link(product.asin),
                            bot_username or "IlTuoBot"
                        )
                        
                        await bot.send_message(
                            chat_id=settings.TELEGRAM_CHANNEL_ID,
                            text=channel_msg,
                            parse_mode='HTML',
                            disable_web_page_preview=False
                        )
                        logger.info(f"Broadcasted deal to channel {settings.TELEGRAM_CHANNEL_ID}: {product.asin} (-{discount_percent:.1f}%)")
                    except Exception as e:
                        logger.error(f"Failed to broadcast to channel: {e}")

        # Calculate price statistics for FOMO messages
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        price_stats = {
            'is_historical_min': False,
            'is_6_month_min': False,
            'avg_price': None,
            'percent_below_avg': None,
            'days_since_lowest': None,
        }
        
        if price_dropped:
            # Get price history for statistics (last 6 months)
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            price_history_all = db.query(PriceHistory).filter(
                PriceHistory.product_id == product.id,
                PriceHistory.checked_at >= six_months_ago
            ).all()
            
            if price_history_all:
                prices = [ph.price for ph in price_history_all]
                min_price_6m = min(prices)
                avg_price = sum(prices) / len(prices)
                
                # Check if current price is historical minimum (all time)
                all_time_min = db.query(func.min(PriceHistory.price)).filter(
                    PriceHistory.product_id == product.id
                ).scalar()
                
                if all_time_min is not None:
                    if current_price <= all_time_min:
                        price_stats['is_historical_min'] = True
                else:
                    price_stats['is_historical_min'] = True
                
                # Check if current price is 6-month minimum
                if current_price <= min_price_6m:
                    price_stats['is_6_month_min'] = True
                
                # Calculate percentage below average
                if avg_price and current_price < avg_price:
                    price_stats['avg_price'] = avg_price
                    price_stats['percent_below_avg'] = ((avg_price - current_price) / avg_price) * 100
                
                # Find when the lowest price was seen (if not current minimum)
                if not price_stats['is_historical_min'] and all_time_min is not None:
                    lowest_price_record = db.query(PriceHistory.checked_at).filter(
                        PriceHistory.product_id == product.id,
                        PriceHistory.price == all_time_min
                    ).order_by(PriceHistory.checked_at.asc()).first()
                    
                    if lowest_price_record and lowest_price_record[0]:
                        days_diff = (datetime.utcnow() - lowest_price_record[0]).days
                        price_stats['days_since_lowest'] = days_diff
        
        if price_dropped:
            
            # Get all users watching this product
            user_products = db.query(UserProduct).filter(
                UserProduct.product_id == product.id
            ).all()
            
            if not user_products:
                logger.warning(f"[{product.asin}] Price dropped but no users watching this product!")
            else:
                logger.info(f"[{product.asin}] Sending notifications to {len(user_products)} user(s)")
            
            # Generate affiliate link
            affiliate_link = generate_affiliate_link(product.asin)
            
            # Send notification to each user
            for user_product in user_products:
                try:
                    user_id = user_product.user_id
                    
                    # Prepare product dict for message
                    product_dict = {
                        'asin': product.asin,
                        'title': product.title or 'Prodotto',
                    }
                    
                    message = get_price_drop_notification(
                        product_dict,
                        comparison_price,
                        current_price,
                        currency,
                        affiliate_link,
                        bot_username,
                        price_stats
                    )
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    
                    logger.info(f"Sent price drop notification to user {user_id} for product {product.asin}")
                    
                except Exception as e:
                    logger.error(f"Error sending notification to user {user_product.user_id}: {e}")
                    continue
        
        db.commit()
        logger.debug(f"Successfully checked product {product.asin}: {current_price} {currency}")
        
    except Exception as e:
        logger.error(f"Error checking product {product.asin} using {method}: {e}")
        db.rollback()



async def check_prices_job_vip(bot: Bot):
    """
    Job to check prices for VIP users: every minute, checks products watched by VIP users.
    Uses PA-API if enabled, otherwise uses web scraping.
    Updates price_history table and sends notifications when prices drop.
    
    Args:
        bot: Telegram Bot instance
    """
    global _product_index
    
    db: Session = SessionLocal()
    
    # Get bot username
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    # Initialize price fetcher based on configuration
    if settings.ENABLE_PA_API:
        try:
            price_fetcher = AmazonAPIClient()
            method = "PA-API"
        except Exception as e:
            logger.error(f"Failed to initialize PA-API client: {e}. Falling back to scraping.")
            price_fetcher = AmazonScraper()
            method = "Scraping"
    else:
        price_fetcher = AmazonScraper()
        method = "Scraping"
    
    try:
        from database.models import User
        
        # Get all active products watched by VIP users
        products = db.query(Product).join(UserProduct).join(User).filter(
            User.is_vip == True
        ).distinct().order_by(Product.id).all()
        
        if not products:
            logger.debug("No VIP products to check")
            return
        
        # Calculate how many products we can check in this minute (600 products max at 0.1s interval)
        max_products_per_minute = 600  # 60 seconds / 0.1 seconds = 600
        
        # Start rotation from current index
        products_to_check = min(len(products), max_products_per_minute)
        checked_count = 0
        
        logger.info(f"Starting VIP rotation: checking up to {products_to_check} products (1 every 0.1s) using {method}")
        
        while checked_count < products_to_check:
            # Get the next product in rotation
            product = products[_product_index % len(products)]
            _product_index = (_product_index + 1) % len(products)
            
            # Check the product
            await check_single_product(bot, product, price_fetcher, method, db, bot_username)
            checked_count += 1
            
            # Wait 0.1 seconds before checking next product (except for the last one)
            if checked_count < products_to_check:
                await asyncio.sleep(0.1)
        
        logger.info(f"VIP rotation cycle completed: checked {checked_count} products")
        
    except Exception as e:
        logger.error(f"Error in VIP price check job: {e}")
        db.rollback()
    finally:
        db.close()


async def check_prices_job_regular(bot: Bot):
    """
    Job to check prices for regular (non-VIP) users: every 15 minutes, checks products watched by non-VIP users.
    Uses PA-API if enabled, otherwise uses web scraping.
    Updates price_history table and sends notifications when prices drop.
    
    Args:
        bot: Telegram Bot instance
    """
    global _product_index
    
    db: Session = SessionLocal()
    
    # Get bot username
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    # Initialize price fetcher based on configuration
    if settings.ENABLE_PA_API:
        try:
            price_fetcher = AmazonAPIClient()
            method = "PA-API"
        except Exception as e:
            logger.error(f"Failed to initialize PA-API client: {e}. Falling back to scraping.")
            price_fetcher = AmazonScraper()
            method = "Scraping"
    else:
        price_fetcher = AmazonScraper()
        method = "Scraping"
    
    try:
        from database.models import User
        
        # Get all active products watched by non-VIP users
        products = db.query(Product).join(UserProduct).join(User).filter(
            User.is_vip == False
        ).distinct().order_by(Product.id).all()
        
        if not products:
            logger.debug("No regular products to check")
            return
        
        # Calculate how many products we can check in 15 minutes (9000 products max at 0.1s interval)
        max_products_per_cycle = 9000  # 15 minutes * 60 seconds / 0.1 seconds = 9000
        
        # Start rotation from current index
        products_to_check = min(len(products), max_products_per_cycle)
        checked_count = 0
        
        logger.info(f"Starting regular rotation: checking up to {products_to_check} products (1 every 0.1s) using {method}")
        
        while checked_count < products_to_check:
            # Get the next product in rotation
            product = products[_product_index % len(products)]
            _product_index = (_product_index + 1) % len(products)
            
            # Check the product
            await check_single_product(bot, product, price_fetcher, method, db, bot_username)
            checked_count += 1
            
            # Wait 0.1 seconds before checking next product (except for the last one)
            if checked_count < products_to_check:
                await asyncio.sleep(0.1)
        
        logger.info(f"Regular rotation cycle completed: checked {checked_count} products")
        
    except Exception as e:
        logger.error(f"Error in regular price check job: {e}")
        db.rollback()
    finally:
        db.close()


async def daily_summary_job(bot: Bot):
    """
    Job to send summary of all products in watchlist to each user.
    Runs every 1 day.
    
    Args:
        bot: Telegram Bot instance
    """
    from database.models import User
    
    db: Session = SessionLocal()
    
    try:
        logger.info("Starting summary job (every 1 day)...")
        
        # Get all users
        users = db.query(User).all()
        
        if not users:
            logger.info("No users found, skipping summary")
            return
        
        logger.info(f"Sending summary to {len(users)} users...")
        
        sent_count = 0
        for user in users:
            try:
                # Get user's products
                user_products = db.query(UserProduct).filter(
                    UserProduct.user_id == user.telegram_id
                ).all()
                
                if not user_products:
                    logger.info(f"User {user.telegram_id} has no products in watchlist, skipping")
                    continue  # Skip users with empty watchlist
                
                logger.info(f"Processing user {user.telegram_id} with {len(user_products)} products")
                
                # Prepare products list
                products = []
                for up in user_products:
                    product = up.product
                    affiliate_link = generate_affiliate_link(product.asin)
                    
                    # Get latest price from history
                    latest_price = db.query(PriceHistory).filter(
                        PriceHistory.product_id == product.id
                    ).order_by(PriceHistory.checked_at.desc()).first()
                    
                    products.append({
                        'asin': product.asin,
                        'title': product.title or f"Prodotto {product.asin}",
                        'initial_price': product.initial_price,
                        'current_price': latest_price.price if latest_price else product.initial_price,
                        'currency': latest_price.currency if latest_price else 'EUR',
                        'affiliate_link': affiliate_link,
                    })
                
                # Send summary
                message = get_daily_summary_message(products)
                
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    logger.info(f"Sent summary to user {user.telegram_id} ({len(products)} products)")
                    sent_count += 1
                except Exception as send_error:
                    logger.error(f"Failed to send summary to user {user.telegram_id}: {send_error}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
                
            except Exception as e:
                logger.error(f"Error processing user {user.telegram_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"Summary job completed: sent to {sent_count} users")
        
    except Exception as e:
        logger.error(f"Error in daily summary job: {e}")
    finally:
        db.close()
