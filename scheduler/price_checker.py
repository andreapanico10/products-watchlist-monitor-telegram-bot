"""Price checker scheduler job."""
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import Product, UserProduct, PriceHistory
from amazon.api_client import AmazonAPIClient
from amazon.scraper import AmazonScraper
from amazon.affiliate import generate_affiliate_link
from bot.messages import get_price_drop_notification, get_daily_summary_message
from telegram import Bot
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


async def check_prices_job(bot: Bot):
    """
    Job to check prices for all products and send notifications.
    Uses PA-API if enabled, otherwise uses web scraping.
    Updates price_history table and sends notifications when prices drop.
    
    Args:
        bot: Telegram Bot instance
    """
    db: Session = SessionLocal()
    
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
        logger.info(f"Starting price check job using {method}...")
        
        # Get all active products (products that have at least one user watching)
        products = db.query(Product).join(UserProduct).distinct().all()
        
        if not products:
            logger.info("No products to check")
            return
        
        logger.info(f"Checking {len(products)} products...")
        
        for product in products:
            try:
                # Get current price using selected method
                product_info = price_fetcher.get_product_info(product.asin)
                
                if not product_info or product_info.get('price') is None:
                    logger.warning(f"Could not get price for product {product.asin} using {method}")
                    continue
                
                current_price = product_info['price']
                currency = product_info.get('currency', 'EUR')
                
                # Update product title if we got a better one
                if product_info.get('title') and not product.title:
                    product.title = product_info['title']
                
                # Update product URL if not set
                if product_info.get('url') and not product.url:
                    product.url = product_info['url']
                
                # Save price to history (always update price_history)
                price_history = PriceHistory(
                    product_id=product.id,
                    price=current_price,
                    currency=currency
                )
                db.add(price_history)
                
                # Update initial_price if not set
                if not product.initial_price:
                    product.initial_price = current_price
                
                # Check if price dropped
                price_dropped = False
                comparison_price = None
                
                # Compare with target price if set, otherwise with initial price
                if product.target_price and current_price < product.target_price:
                    price_dropped = True
                    comparison_price = product.target_price
                elif product.initial_price and current_price < product.initial_price:
                    price_dropped = True
                    comparison_price = product.initial_price
                
                if price_dropped:
                    # Get all users watching this product
                    user_products = db.query(UserProduct).filter(
                        UserProduct.product_id == product.id
                    ).all()
                    
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
                                affiliate_link
                            )
                            
                            await bot.send_message(
                                chat_id=user_id,
                                text=message,
                                parse_mode='Markdown',
                                disable_web_page_preview=False
                            )
                            
                            logger.info(f"Sent price drop notification to user {user_id} for product {product.asin}")
                            
                        except Exception as e:
                            logger.error(f"Error sending notification to user {user_product.user_id}: {e}")
                            continue
                
            except Exception as e:
                logger.error(f"Error checking product {product.asin} using {method}: {e}")
                continue
        
        db.commit()
        logger.info(f"Price check job completed successfully using {method}")
        
    except Exception as e:
        logger.error(f"Error in price check job: {e}")
        db.rollback()
    finally:
        db.close()


async def daily_summary_job(bot: Bot):
    """
    Job to send daily summary of all products in watchlist to each user.
    This is a separate job that can run alongside price checking.
    
    Args:
        bot: Telegram Bot instance
    """
    from database.models import User
    
    db: Session = SessionLocal()
    
    try:
        logger.info("Starting daily summary job...")
        
        # Get all users
        users = db.query(User).all()
        
        logger.info(f"Sending daily summary to {len(users)} users...")
        
        for user in users:
            try:
                # Get user's products
                user_products = db.query(UserProduct).filter(
                    UserProduct.user_id == user.telegram_id
                ).all()
                
                if not user_products:
                    continue  # Skip users with empty watchlist
                
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
                
                # Send daily summary
                message = get_daily_summary_message(products)
                
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=False
                )
                
                logger.info(f"Sent daily summary to user {user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Error sending daily summary to user {user.telegram_id}: {e}")
                continue
        
        logger.info("Daily summary job completed successfully")
        
    except Exception as e:
        logger.error(f"Error in daily summary job: {e}")
    finally:
        db.close()
