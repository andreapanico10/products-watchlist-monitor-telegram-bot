"""Inline keyboards for Telegram bot interactions."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict


def create_watchlist_keyboard(products: List[Dict]) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for watchlist with remove buttons.
    
    Args:
        products: List of product dictionaries with 'asin' and 'title'
        
    Returns:
        InlineKeyboardMarkup with remove buttons
    """
    if not products:
        return None
    
    keyboard = []
    for product in products:
        asin = product.get('asin', '')
        title = product.get('title', 'Prodotto')
        # Truncate title if too long
        if len(title) > 50:
            title = title[:47] + "..."
        
        button = InlineKeyboardButton(
            f"🗑️ Rimuovi: {title}",
            callback_data=f"remove_{asin}"
        )
        keyboard.append([button])
    
    return InlineKeyboardMarkup(keyboard)


def create_remove_confirmation_keyboard(asin: str) -> InlineKeyboardMarkup:
    """
    Create confirmation keyboard for product removal.
    
    Args:
        asin: Product ASIN
        
    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Conferma", callback_data=f"confirm_remove_{asin}"),
            InlineKeyboardButton("❌ Annulla", callback_data="cancel_remove")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
