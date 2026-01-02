import logging
import random
import time
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
from config.settings import settings

logger = logging.getLogger(__name__)


class AmazonScraper:
    """Scraper for Amazon product pages."""
    
    def __init__(self):
        self.region = settings.AMAZON_REGION
        self.last_request_time = 0
        self.min_request_interval = 0.5
        
        # List of realistic User-Agents to rotate
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        
        self.session = requests.Session()
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
        self._warmup_session()
    
    def _rate_limit(self):
        """Enforce rate limiting with slight random jitter."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Add a 20-50% random jitter to the wait time to look less like a bot
        jitter = random.uniform(1.0, 1.5)
        required_wait = self.min_request_interval * jitter
        
        if time_since_last < required_wait:
            sleep_time = required_wait - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _warmup_session(self):
        """Initial call to get basic cookies from Amazon."""
        try:
            logger.info(f"Warming up scraper session on {self.domain}...")
            self.session.headers.update(self._get_headers())
            self.session.get(f"https://www.{self.domain}/", timeout=10)
        except Exception as e:
            logger.warning(f"Session warmup failed: {e}")
    
    def _get_headers(self, with_referer=True) -> Dict[str, str]:
        """Get HTTP headers that mimic a real browser with rotation."""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        if with_referer:
            referers = [
                'https://www.google.com/',
                'https://www.bing.com/',
                f'https://www.{self.domain}/',
                'https://www.facebook.com/'
            ]
            headers['Referer'] = random.choice(referers)
            
        return headers
    
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
            # Rotate headers for each request
            headers = self._get_headers()
            self.session.headers.update(headers)
            logger.info(f"[{asin}] Using User-Agent: {headers['User-Agent'][:50]}...")
            
            # Reusing the existing session for better performance and cookie handling
            response = self.session.get(url, timeout=15)
            logger.info(f"[{asin}] Scraper request status: {response.status_code}")
            response.raise_for_status()
            
            # Check for CAPTCHA or Robot Check
            if "api-services-support@amazon.com" in response.text or "robot checkpoint" in response.text.lower():
                logger.error(f"[{asin}] Amazon Robot Check/CAPTCHA detected!")
                return None

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
        """Extract price from page using targeted selectors to avoid sponsored products."""
        
        # 1. Define main price containers (ordered by reliability)
        main_price_containers = [
            '#corePrice_desktop',
            '#corePrice_feature_div',
            '#corePriceDisplay_desktop_feature_div',
            '#apex_desktop',
            '#price_inside_buybox',
            '#newBuyBoxPrice',
            '#priceblock_ourprice',
            '#priceblock_dealprice'
        ]
        
        # 2. Try to find the price ONLY inside these main containers
        for container_selector in main_price_containers:
            container = soup.select_one(container_selector)
            if not container:
                continue
                
            # Strategy: Look for the 'offscreen' price first (usually the most reliable clean text)
            offscreen = container.select_one('.a-offscreen')
            if offscreen:
                price_text = offscreen.get_text(strip=True)
                price = self._extract_price_from_text(price_text)
                if price:
                    logger.info(f"Price found in {container_selector} (.a-offscreen): {price}")
                    return price
            
            # Strategy: Look for the whole/fraction components within the main container
            price_whole = container.select_one('.a-price-whole')
            price_fraction = container.select_one('.a-price-fraction')
            if price_whole and price_fraction:
                whole_text = price_whole.get_text(strip=True).replace('.', '').replace(',', '')
                fraction_text = price_fraction.get_text(strip=True)
                try:
                    price = float(f"{whole_text}.{fraction_text}")
                    logger.info(f"Price found in {container_selector} (whole/fraction): {price}")
                    return price
                except ValueError:
                    pass
        
        # 3. Fallback: If no price in main containers, search for any a-price that is NOT in a carousel/sponsored block
        # This is a bit risky but can catch unusual layouts
        all_prices = soup.select('.a-price .a-offscreen')
        for p in all_prices:
            # Check if this price is inside a suspicious container
            parent_text = ""
            current = p
            for _ in range(10): # Look up 10 levels
                if not current.parent: break
                current = current.parent
                if current.get('id'): parent_text += " " + current.get('id')
                if current.get('class'): parent_text += " " + " ".join(current.get('class'))
            
            # Skip if inside common 'other products' blocks
            bad_keywords = ['sponsored', 'carousel', 'similar', 'related', 'bundle', 'upsell', 'accessory']
            if any(k in parent_text.lower() for k in bad_keywords):
                continue
                
            price = self._extract_price_from_text(p.get_text(strip=True))
            if price:
                logger.info(f"Price found via fallback (safe filtered): {price}")
                return price

        logger.debug("No valid price found after targeted and filtered search")
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

