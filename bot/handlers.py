"""Telegram bot handlers."""
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Product, UserProduct, PriceHistory
from amazon.parser import extract_asin_from_url
from amazon.api_client import AmazonAPIClient
from amazon.scraper import AmazonScraper
from amazon.affiliate import generate_affiliate_link, generate_base_affiliate_link
from bot.messages import (
    get_welcome_message,
    get_product_added_message,
    get_product_not_found_message,
    get_watchlist_message,
    get_product_removed_message,
    get_product_not_in_watchlist_message,
    get_error_message,
    get_channel_deal_message,
    get_channel_info_message,
)
from bot.keyboards import create_watchlist_keyboard, create_remove_confirmation_keyboard
from config.settings import settings


def get_or_create_user(db: Session, telegram_user, referrer_id: int = None) -> User:
    """
    Get or create user from Telegram user object, updating all available information.
    
    Args:
        db: Database session
        telegram_user: Telegram User object from update.effective_user
        referrer_id: Optional referrer telegram_id if user came from referral link
        
    Returns:
        User database object
    """
    db_user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
    is_new_user = False
    
    if not db_user:
        # Create new user
        is_new_user = True
        db_user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=getattr(telegram_user, 'last_name', None),
            language_code=getattr(telegram_user, 'language_code', None),
            is_bot=getattr(telegram_user, 'is_bot', False),
            is_premium=getattr(telegram_user, 'is_premium', None),
            referrer_id=referrer_id,
            is_vip=False,
            referral_count=0,
            product_limit=3,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # If new user has referrer, update referrer's stats will be done after
        # (we need bot access to send notification)
    else:
        # Update existing user information (in case it changed)
        db_user.username = telegram_user.username
        db_user.first_name = telegram_user.first_name
        db_user.last_name = getattr(telegram_user, 'last_name', None)
        db_user.language_code = getattr(telegram_user, 'language_code', None)
        db_user.is_bot = getattr(telegram_user, 'is_bot', False)
        db_user.is_premium = getattr(telegram_user, 'is_premium', None)
        
        # Set referrer only if not already set (first time registration via referral)
        if referrer_id and not db_user.referrer_id:
            db_user.referrer_id = referrer_id
            db.commit()
            # process_referral will be called after with bot access
        else:
            db.commit()
    
    return db_user


async def process_referral(db: Session, referrer_id: int, bot=None):
    """
    Process a referral: update referrer's referral_count, VIP status, and product_limit.
    Optionally sends a notification to the referrer.
    
    Args:
        db: Database session
        referrer_id: Telegram ID of the referrer
        bot: Optional Telegram Bot instance to send notification
    """
    referrer = db.query(User).filter(User.telegram_id == referrer_id).first()
    if not referrer:
        return
    
    old_count = referrer.referral_count
    was_vip = referrer.is_vip
    
    # Increment referral count
    referrer.referral_count += 1
    
    # Update VIP status: 3 referrals = VIP
    if referrer.referral_count >= 3 and not referrer.is_vip:
        referrer.is_vip = True
    
    # Update product limit:
    # Base: 3 products
    # With 3 referrals: 5 products
    # Each additional referral: +1 product
    if referrer.referral_count == 3:
        referrer.product_limit = 5
    elif referrer.referral_count > 3:
        referrer.product_limit = 5 + (referrer.referral_count - 3)
    
    db.commit()
    
    # Send notification to referrer if bot is provided
    if bot:
        try:
            new_referral_count = referrer.referral_count
            message = f"""🎉 **Nuovo referral!**

Qualcuno si è iscritto usando il tuo codice referral!

👥 **I tuoi referral:** {old_count} → {new_referral_count}"""
            
            # Add VIP status update if they just became VIP
            if not was_vip and referrer.is_vip:
                message += "\n\n⭐ **Congratulazioni! Sei diventato VIP!**\nOra ricevi notifiche anticipate sugli sconti!"
            
            # Add product limit update
            if referrer.product_limit > 3:
                message += f"\n\n📦 **Limite prodotti aumentato a {referrer.product_limit}**"
            
            message += "\n\nUsa /referral per vedere tutte le tue statistiche!"
            
            await bot.send_message(
                chat_id=referrer_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            # Log error but don't fail the referral processing
            print(f"Error sending referral notification to {referrer_id}: {e}")


def get_user_referral_stats(db: Session, user_id: int) -> dict:
    """
    Get referral statistics for a user.
    
    Args:
        db: Database session
        user_id: Telegram user ID
        
    Returns:
        Dictionary with referral stats
    """
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return None
    
    return {
        'referral_count': user.referral_count,
        'is_vip': user.is_vip,
        'product_limit': user.product_limit,
        'current_products': db.query(UserProduct).filter(UserProduct.user_id == user_id).count(),
    }


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with optional referral parameter."""
    user = update.effective_user
    db = next(get_db())
    
    try:
        # Check for referral parameter in command args
        referrer_id = None
        if context.args and len(context.args) > 0:
            ref_param = context.args[0]
            if ref_param.startswith('ref_'):
                try:
                    referrer_id = int(ref_param.replace('ref_', ''))
                    # Verify referrer exists and is not the same user
                    if referrer_id == user.id:
                        referrer_id = None
                    else:
                        referrer = db.query(User).filter(User.telegram_id == referrer_id).first()
                        if not referrer:
                            referrer_id = None
                except ValueError:
                    referrer_id = None
        
        # Create or get user (with referral if provided)
        db_user = get_or_create_user(db, user, referrer_id=referrer_id)
        
        # Process referral if user came via referral link (with bot for notification)
        # This happens when:
        # 1. New user registered with referral link
        # 2. Existing user registered with referral link for the first time
        if referrer_id and db_user.referrer_id == referrer_id:
            bot = context.bot
            await process_referral(db, referrer_id, bot=bot)
            # Refresh user to get updated referral info
            db.refresh(db_user)
        
        # Generate base affiliate link for homepage
        base_link = generate_base_affiliate_link()
        
        # Get referral link for this user
        bot = context.bot
        bot_info = await bot.get_me()
        referral_link = f"t.me/{bot_info.username}?start=ref_{user.id}"
        
        await update.message.reply_text(
            get_welcome_message(base_link, db_user, referral_link), 
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error in start_command: {e}")
        import traceback
        traceback.print_exc()
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
            
            # Get current price from price history (latest entry)
            latest_price_history = db.query(PriceHistory).filter(
                PriceHistory.product_id == product.id
            ).order_by(PriceHistory.checked_at.desc()).first()
            
            current_price = None
            currency = 'EUR'
            if latest_price_history:
                current_price = latest_price_history.price
                currency = latest_price_history.currency or 'EUR'
            elif product.initial_price:
                # If no history, use initial price as current
                current_price = product.initial_price
            
            products.append({
                'asin': product.asin,
                'title': product.title or 'Prodotto senza titolo',
                'initial_price': product.initial_price,
                'current_price': current_price,
                'target_price': product.target_price,
                'currency': currency,
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
        
        # Check product limit
        current_product_count = db.query(UserProduct).filter(
            UserProduct.user_id == user.id
        ).count()
        
        if current_product_count >= db_user.product_limit:
            bot = context.bot
            bot_info = await bot.get_me()
            referral_link = f"t.me/{bot_info.username}?start=ref_{user.id}"
            
            await update.message.reply_text(
                f"⚠️ **Limite raggiunto!**\n\n"
                f"Hai raggiunto il limite di {db_user.product_limit} prodotti monitorati.\n\n"
                f"💡 **Invita amici per aumentare il limite:**\n"
                f"• Base: 3 prodotti\n"
                f"• Con 3 referral: 5 prodotti\n"
                f"• Ogni referral aggiuntivo: +1 prodotto\n\n"
                f"🔗 **Il tuo link referral:**\n`{referral_link}`\n\n"
                f"Usa /referral per vedere le tue statistiche!\n\n"
                f"📢 **Nel canale pubblichiamo i migliori sconti già filtrati:**\n"
                f"👉 @ScontiAmazonWatchlist",
                parse_mode='Markdown'
            )
            return
        
        # Check if this is user's first product (for referral tracking)
        existing_products_count = db.query(UserProduct).filter(
            UserProduct.user_id == user.id
        ).count()
        is_first_product = existing_products_count == 0
        
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
        
        # If this is the first product and user has a referrer, process referral
        if is_first_product and db_user.referrer_id:
            bot = context.bot
            await process_referral(db, db_user.referrer_id, bot=bot)
        
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


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /referral command to show referral stats and link."""
    user = update.effective_user
    db = next(get_db())
    
    try:
        # Get or create user
        db_user = get_or_create_user(db, user)
        
        # Get referral stats
        stats = get_user_referral_stats(db, user.id)
        
        # Get bot username for referral link
        bot = context.bot
        bot_info = await bot.get_me()
        referral_link = f"t.me/{bot_info.username}?start=ref_{user.id}"
        
        # Build message
        vip_status = "✅ VIP" if stats['is_vip'] else "❌ Non VIP"
        vip_benefits = ""
        if stats['is_vip']:
            vip_benefits = "\n\n⭐ **Benefici VIP:**\n• Controllo prezzi ogni minuto (15 min prima degli altri)\n• Notifiche anticipate sugli sconti"
        else:
            referrals_needed = 3 - stats['referral_count']
            vip_benefits = f"\n\n🎯 **Diventa VIP:**\nInvita ancora {referrals_needed} amico/i per diventare VIP e ricevere notifiche anticipate!"
        
        message = f"""📊 **Le tue statistiche referral:**

👥 **Referral:** {stats['referral_count']}
⭐ **Status:** {vip_status}
📦 **Limite prodotti:** {stats['product_limit']}
📋 **Prodotti attuali:** {stats['current_products']}/{stats['product_limit']}
{vip_benefits}

🔗 **Il tuo link referral:**
`{referral_link}`

💡 **Come funziona:**
• Condividi il link con i tuoi amici
• Quando si registrano e aggiungono un prodotto, ottieni punti
• 3 referral = diventi VIP
• Ogni referral aumenta il limite prodotti"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error in referral_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(get_error_message())
    finally:
        db.close()


async def canale_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /canale command to show channel information."""
    try:
        await update.message.reply_text(get_channel_info_message(), parse_mode='Markdown')
    except Exception as e:
        print(f"Error in canale_command: {e}")
        await update.message.reply_text(get_error_message())


def register_handlers(application):
    """Register all bot handlers."""
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("referral", referral_command))
    application.add_handler(CommandHandler("canale", canale_command))
    
    # Message handlers (Amazon links)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_amazon_link
    ))
    
    # Callback query handler (inline keyboards)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
