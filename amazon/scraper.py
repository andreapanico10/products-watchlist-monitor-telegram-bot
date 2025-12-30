"""Web scraper for Amazon product pages to extract prices."""
import re
import time
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class AmazonScraper:
    """Scraper for Amazon product pages."""
    
    def __init__(self):
        self.region = settings.AMAZON_REGION
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Be respectful: 2 seconds between requests
        
        # Map region to domain
        self.domain_map = {
            'IT': 'amazon.it',
            'US': 'amazon.com',
            'UK': 'amazon.co.uk',
            'DE': 'amazon.de',
            'FR': 'amazon.fr',
            'ES': 'amazon.es',
            'CA': 'amazon.ca',
            'JP': 'amazon.co.jp',
            'AU': 'amazon.com.au',
        }
        
        self.domain = self.domain_map.get(self.region.upper(), 'amazon.it')
    
    def _rate_limit(self):
        """Enforce rate limiting to avoid being blocked."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers that mimic a real browser."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def _extract_price_from_text(self, price_text: str) -> Optional[float]:
        """
        Extract numeric price from text string.
        
        Args:
            price_text: Price text (e.g., "€29,99", "29.99 EUR", "$19.99", "1.299,99")
            
        Returns:
            Price as float or None if not found
        """
        if not price_text:
            return None
        
        # Remove currency symbols and clean
        price_text = price_text.strip()
        # Remove common currency symbols
        price_text = re.sub(r'[€$£¥]', '', price_text).strip()
        
        # Try to match different price formats
        # European format: 1.299,99 or 29,99 (thousands with dot, decimals with comma)
        european_match = re.search(r'(\d{1,3}(?:\.\d{3})*),(\d{2})', price_text)
        if european_match:
            whole_part = european_match.group(1).replace('.', '')  # Remove thousand separators
            decimal_part = european_match.group(2)
            try:
                return float(f"{whole_part}.{decimal_part}")
            except ValueError:
                pass
        
        # American format: 1,299.99 or 29.99 (thousands with comma, decimals with dot)
        american_match = re.search(r'(\d{1,3}(?:,\d{3})*)\.(\d{2})', price_text)
        if american_match:
            whole_part = american_match.group(1).replace(',', '')  # Remove thousand separators
            decimal_part = american_match.group(2)
            try:
                return float(f"{whole_part}.{decimal_part}")
            except ValueError:
                pass
        
        # Simple format with comma: 29,99
        simple_comma_match = re.search(r'(\d+),(\d{2})', price_text)
        if simple_comma_match:
            try:
                return float(f"{simple_comma_match.group(1)}.{simple_comma_match.group(2)}")
            except ValueError:
                pass
        
        # Simple format with dot: 29.99
        simple_dot_match = re.search(r'(\d+)\.(\d{2})', price_text)
        if simple_dot_match:
            try:
                return float(f"{simple_dot_match.group(1)}.{simple_dot_match.group(2)}")
            except ValueError:
                pass
        
        # Integer only: 29
        integer_match = re.search(r'(\d+)', price_text)
        if integer_match:
            try:
                return float(integer_match.group(1))
            except ValueError:
                pass
        
        return None
    
    def get_product_info(self, asin: str) -> Optional[Dict]:
        """
        Scrape product information from Amazon product page.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Dictionary with product info including price and title, or None if error
        """
        self._rate_limit()
        
        url = f"https://www.{self.domain}/dp/{asin}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            product_info = {
                'asin': asin,
                'title': self._extract_title(soup),
                'price': self._extract_price(soup),
                'currency': self._get_currency(),
                'availability': self._extract_availability(soup),
                'url': url,  # Include the product URL
            }
            
            return product_info if product_info['price'] is not None else None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping product {asin}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping product {asin}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from page."""
        # Try multiple selectors for title
        title_selectors = [
            '#productTitle',
            'h1.a-size-large',
            'span#productTitle',
            'h1 span',
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    return title
        
        return ''
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from page using multiple strategies."""
        # Strategy 1: New Amazon format with separate whole and fraction parts
        price_whole_elem = soup.select_one('.a-price-whole')
        price_fraction_elem = soup.select_one('.a-price-fraction')
        if price_whole_elem and price_fraction_elem:
            whole_text = price_whole_elem.get_text(strip=True).replace('.', '').replace(',', '')
            fraction_text = price_fraction_elem.get_text(strip=True)
            try:
                return float(f"{whole_text}.{fraction_text}")
            except ValueError:
                pass
        
        # Strategy 2: Try various price selectors (Amazon has different layouts)
        price_selectors = [
            '#priceblock_ourprice',  # Main price
            '#priceblock_dealprice',  # Deal price
            '#priceblock_saleprice',  # Sale price
            '.a-price .a-offscreen',  # Hidden price (accessible)
            'span.a-price[data-a-color="base"] span.a-offscreen',  # Base price
            'span.a-price[data-a-color="price"] span.a-offscreen',  # Price color
            '.a-price-range .a-price-whole',  # Price range
            '#twister-plus-price-data-price',  # Price data attribute
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                if not price_text:
                    # Try data attribute
                    price_text = price_elem.get('data-a-price', '')
                
                price = self._extract_price_from_text(price_text)
                if price:
                    return price
        
        # Strategy 2: Try to find price in JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    offers = data.get('offers', {})
                    if isinstance(offers, dict):
                        price = offers.get('price')
                        if price:
                            try:
                                return float(price)
                            except (ValueError, TypeError):
                                pass
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # Strategy 3: Search for price pattern in page text
        price_patterns = [
            r'€\s*(\d+[.,]\d{2})',
            r'(\d+[.,]\d{2})\s*€',
            r'\$\s*(\d+[.,]\d{2})',
            r'(\d+[.,]\d{2})\s*USD',
        ]
        
        page_text = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, page_text)
            if match:
                price = self._extract_price_from_text(match.group(0))
                if price:
                    return price
        
        return None
    
    def _extract_availability(self, soup: BeautifulSoup) -> str:
        """Extract product availability status."""
        availability_selectors = [
            '#availability span',
            '#availability',
            '.a-color-state',
            '#outOfStock',
        ]
        
        for selector in availability_selectors:
            avail_elem = soup.select_one(selector)
            if avail_elem:
                text = avail_elem.get_text(strip=True)
                if text:
                    return text
        
        return 'Unknown'
    
    def _get_currency(self) -> str:
        """Get currency symbol based on region."""
        currency_map = {
            'IT': 'EUR',
            'US': 'USD',
            'UK': 'GBP',
            'DE': 'EUR',
            'FR': 'EUR',
            'ES': 'EUR',
            'CA': 'CAD',
            'JP': 'JPY',
            'AU': 'AUD',
        }
        return currency_map.get(self.region.upper(), 'EUR')
    
    def get_product_price(self, asin: str) -> Optional[float]:
        """
        Get current price for a product.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Current price as float, or None if error
        """
        product_info = self.get_product_info(asin)
        if product_info:
            return product_info.get('price')
        return None

