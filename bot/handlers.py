"""Telegram bot handlers."""
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Product, UserProduct, PriceHistory
from amazon.parser import extract_asin_from_url
from amazon.api_client import AmazonAPIClient
from amazon.scraper import AmazonScraper
from amazon.affiliate import generate_affiliate_link
from bot.messages import (
    get_welcome_message,
    get_product_added_message,
    get_product_not_found_message,
    get_watchlist_message,
    get_product_removed_message,
    get_product_not_in_watchlist_message,
    get_error_message,
)
from bot.keyboards import create_watchlist_keyboard, create_remove_confirmation_keyboard
from config.settings import settings


def get_or_create_user(db: Session, telegram_user) -> User:
    """
    Get or create user from Telegram user object, updating all available information.
    
    Args:
        db: Database session
        telegram_user: Telegram User object from update.effective_user
        
    Returns:
        User database object
    """
    db_user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
    
    if not db_user:
        # Create new user
        db_user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=getattr(telegram_user, 'last_name', None),
            language_code=getattr(telegram_user, 'language_code', None),
            is_bot=getattr(telegram_user, 'is_bot', False),
            is_premium=getattr(telegram_user, 'is_premium', None),
        )
        db.add(db_user)
    else:
        # Update existing user information (in case it changed)
        db_user.username = telegram_user.username
        db_user.first_name = telegram_user.first_name
        db_user.last_name = getattr(telegram_user, 'last_name', None)
        db_user.language_code = getattr(telegram_user, 'language_code', None)
        db_user.is_bot = getattr(telegram_user, 'is_bot', False)
        db_user.is_premium = getattr(telegram_user, 'is_premium', None)
    
    db.commit()
    return db_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db = next(get_db())
    
    try:
        # Create or get user (with all available information)
        db_user = get_or_create_user(db, user)
        
        await update.message.reply_text(get_welcome_message(), parse_mode='Markdown')
    except Exception as e:
        print(f"Error in start_command: {e}")
        await update.message.reply_text(get_error_message())
    finally:
        db.close()


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /watchlist command."""
    user = update.effective_user
    db = next(get_db())
    
    try:
        # Get or create user (update user info if needed)
        db_user = get_or_create_user(db, user)
        
        user_products = db.query(UserProduct).filter(UserProduct.user_id == user.id).all()
        
        if not user_products:
            await update.message.reply_text("La tua watchlist è vuota.\n\nInvia un link Amazon per aggiungere un prodotto!")
            return
        
        # Prepare products list
        products = []
        for up in user_products:
            product = up.product
            affiliate_link = generate_affiliate_link(product.asin)
            products.append({
                'asin': product.asin,
                'title': product.title or 'Prodotto senza titolo',
                'initial_price': product.initial_price,
                'target_price': product.target_price,
                'currency': 'EUR',
                'affiliate_link': affiliate_link,
            })
        
        message = get_watchlist_message(products)
        keyboard = create_watchlist_keyboard(products)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        print(f"Error in watchlist_command: {e}")
        await update.message.reply_text(get_error_message())
    finally:
        db.close()


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove <asin> command."""
    user = update.effective_user
    db = next(get_db())
    
    try:
        if not context.args or len(context.args) == 0:
            await update.message.reply_text("Utilizzo: /remove <asin>\n\nEsempio: /remove B08N5WRWNW")
            return
        
        asin = context.args[0].upper()
        
        # Find user product (update user info if needed)
        db_user = get_or_create_user(db, user)
        
        product = db.query(Product).filter(Product.asin == asin).first()
        if not product:
            await update.message.reply_text(get_product_not_in_watchlist_message())
            return
        
        user_product = db.query(UserProduct).filter(
            UserProduct.user_id == user.id,
            UserProduct.product_id == product.id
        ).first()
        
        if not user_product:
            await update.message.reply_text(get_product_not_in_watchlist_message())
            return
        
        # Remove user product
        db.delete(user_product)
        db.commit()
        
        await update.message.reply_text(get_product_removed_message(asin), parse_mode='Markdown')
    except Exception as e:
        print(f"Error in remove_command: {e}")
        await update.message.reply_text(get_error_message())
    finally:
        db.close()


async def handle_amazon_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Amazon link messages."""
    user = update.effective_user
    message_text = update.message.text
    db = next(get_db())
    
    try:
        # Extract ASIN from URL
        asin = extract_asin_from_url(message_text)
        if not asin:
            await update.message.reply_text(get_product_not_found_message())
            return
        
        # Check if product already exists
        product = db.query(Product).filter(Product.asin == asin).first()
        
        # Generate product URL (always available)
        from amazon.affiliate import generate_affiliate_link
        product_url = generate_affiliate_link(asin)
        # Remove affiliate tag for storage (we'll add it when needed)
        if '?tag=' in product_url:
            product_url = product_url.split('?tag=')[0]
        
        # Get product info based on PA-API availability
        product_title = None
        product_price = None
        currency = 'EUR'
        
        if settings.ENABLE_PA_API:
            # Use PA-API to get product info
            try:
                api_client = AmazonAPIClient()
                product_info = api_client.get_product_info(asin)
                
                if product_info:
                    product_title = product_info.get('title', '')
                    product_price = product_info.get('price')
                    currency = product_info.get('currency', 'EUR')
                    # Use URL from API if available, otherwise use generated one
                    product_url = product_info.get('url', product_url)
            except Exception as e:
                print(f"Error getting product info from PA-API: {e}")
                # Fallback to scraping
                try:
                    scraper = AmazonScraper()
                    product_info = scraper.get_product_info(asin)
                    if product_info:
                        product_title = product_info.get('title', '')
                        product_price = product_info.get('price')
                        currency = product_info.get('currency', 'EUR')
                        product_url = product_info.get('url', product_url)
                    else:
                        product_title = f"Prodotto {asin}"
                except Exception as scrape_error:
                    print(f"Error getting product info from scraping: {scrape_error}")
                    product_title = f"Prodotto {asin}"
        else:
            # PA-API not enabled: use web scraping
            try:
                scraper = AmazonScraper()
                product_info = scraper.get_product_info(asin)
                
                if product_info:
                    product_title = product_info.get('title', '')
                    product_price = product_info.get('price')
                    currency = product_info.get('currency', 'EUR')
                    product_url = product_info.get('url', product_url)
                else:
                    product_title = f"Prodotto {asin}"
            except Exception as e:
                print(f"Error getting product info from scraping: {e}")
                product_title = f"Prodotto {asin}"
        
        # Create or update product
        if product:
            # Update product if needed
            if not product.title and product_title:
                product.title = product_title
            if not product.url:
                product.url = product_url
            if product_price and not product.initial_price:
                product.initial_price = product_price
            db.commit()
        else:
            # Create new product
            product = Product(
                asin=asin,
                title=product_title,
                url=product_url,
                initial_price=product_price,
                affiliate_code=settings.AMAZON_AFFILIATE_TAG,
            )
            db.add(product)
            db.commit()
            db.refresh(product)
        
        # Check if user already has this product (create/update user info)
        db_user = get_or_create_user(db, user)
        
        user_product = db.query(UserProduct).filter(
            UserProduct.user_id == user.id,
            UserProduct.product_id == product.id
        ).first()
        
        if user_product:
            await update.message.reply_text(
                f"ℹ️ Questo prodotto è già nella tua watchlist!\n\n"
                f"📦 {product.title or 'Prodotto'}\n"
                f"🔖 ASIN: `{asin}`",
                parse_mode='Markdown'
            )
            return
        
        # Add product to user's watchlist
        user_product = UserProduct(
            user_id=user.id,
            product_id=product.id
        )
        db.add(user_product)
        
        # Save initial price to history if available
        if product_price:
            price_history = PriceHistory(
                product_id=product.id,
                price=product_price,
                currency=currency
            )
            db.add(price_history)
        
        db.commit()
        
        # Generate affiliate link for the message
        affiliate_link = generate_affiliate_link(asin)
        
        # Send confirmation
        message = get_product_added_message(
            product.title or 'Prodotto',
            asin,
            product_price,
            currency,
            affiliate_link
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error in handle_amazon_link: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(get_error_message())
    finally:
        db.close()


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callback queries."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = next(get_db())
    
    try:
        data = query.data
        
        if data.startswith("remove_"):
            asin = data.replace("remove_", "")
            # Show confirmation
            keyboard = create_remove_confirmation_keyboard(asin)
            await query.edit_message_text(
                f"⚠️ Sei sicuro di voler rimuovere il prodotto con ASIN `{asin}` dalla watchlist?",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        elif data.startswith("confirm_remove_"):
            asin = data.replace("confirm_remove_", "")
            
            # Find and remove user product (update user info if needed)
            db_user = get_or_create_user(db, user)
            if db_user:
                product = db.query(Product).filter(Product.asin == asin).first()
                if product:
                    user_product = db.query(UserProduct).filter(
                        UserProduct.user_id == user.id,
                        UserProduct.product_id == product.id
                    ).first()
                    
                    if user_product:
                        db.delete(user_product)
                        db.commit()
                        await query.edit_message_text(
                            get_product_removed_message(asin),
                            parse_mode='Markdown'
                        )
                        return
            
            await query.edit_message_text(get_product_not_in_watchlist_message())
        
        elif data == "cancel_remove":
            await query.edit_message_text("❌ Rimozione annullata.")
        
    except Exception as e:
        print(f"Error in handle_callback_query: {e}")
        await query.edit_message_text(get_error_message())
    finally:
        db.close()


def register_handlers(application):
    """Register all bot handlers."""
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("remove", remove_command))
    
    # Message handlers (Amazon links)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_amazon_link
    ))
    
    # Callback query handler (inline keyboards)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
