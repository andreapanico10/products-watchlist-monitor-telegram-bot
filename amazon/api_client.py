"""Amazon Product Advertising API client."""
import time
import hmac
import hashlib
import json
import requests
from datetime import datetime
from typing import Dict, Optional
from config.settings import settings


class AmazonAPIClient:
    """Client for Amazon Product Advertising API 5.0."""
    
    def __init__(self):
        if not settings.ENABLE_PA_API:
            raise ValueError("PA-API is not enabled. Set ENABLE_PA_API=true in environment variables.")
        
        self.access_key = settings.AMAZON_ACCESS_KEY
        self.secret_key = settings.AMAZON_SECRET_KEY
        self.associate_tag = settings.AMAZON_ASSOCIATE_TAG
        self.region = settings.AMAZON_REGION
        
        # Region endpoints and marketplace IDs
        self.endpoints = {
            'IT': ('webservices.amazon.it', 'APJ6JRA9NG5V4'),
            'US': ('webservices.amazon.com', 'ATVPDKIKX0DER'),
            'UK': ('webservices.amazon.co.uk', 'A1F83G8C2ARO7P'),
            'DE': ('webservices.amazon.de', 'A1PA6795UKMFR9'),
            'FR': ('webservices.amazon.fr', 'A13V1IB3VIYZZH'),
            'ES': ('webservices.amazon.es', 'A1RKKUPIHCS9HS'),
            'CA': ('webservices.amazon.ca', 'A2EUQ1WTGCTBG2'),
            'JP': ('webservices.amazon.co.jp', 'A1VC38T7YXB528'),
            'AU': ('webservices.amazon.com.au', 'A39IBJ37TRP1C6'),
        }
        
        endpoint_info = self.endpoints.get(self.region.upper(), self.endpoints['IT'])
        self.endpoint = endpoint_info[0]
        self.marketplace_id = endpoint_info[1]
        self.last_request_time = 0
        self.min_request_interval = 1.0
    
    def _sign_request(self, method: str, uri: str, payload: str, timestamp: str) -> Dict[str, str]:
        """Generate AWS Signature Version 4 for PA-API 5.0."""
        # Create canonical request
        canonical_uri = uri
        canonical_querystring = ''
        canonical_headers = f'host:{self.endpoint}\nx-amz-date:{timestamp}\n'
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{timestamp[:8]}/{self.region.lower()}/ProductAdvertisingAPI/aws4_request"
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Calculate signature
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        k_date = sign(('AWS4' + self.secret_key).encode('utf-8'), timestamp[:8])
        k_region = sign(k_date, self.region.lower())
        k_service = sign(k_region, 'ProductAdvertisingAPI')
        k_signing = sign(k_service, 'aws4_request')
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Create authorization header
        authorization = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            'Authorization': authorization,
            'X-Amz-Date': timestamp,
        }
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_product_info(self, asin: str) -> Optional[Dict]:
        """
        Get product information from Amazon PA-API 5.0.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Dictionary with product info including price, or None if error
        """
        if not self.access_key or not self.secret_key or not self.associate_tag:
            raise ValueError("Amazon API credentials not configured")
        
        self._rate_limit()
        
        # Prepare request payload
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        payload = {
            'PartnerTag': self.associate_tag,
            'PartnerType': 'Associates',
            'Marketplace': self.marketplace_id,
            'ItemIds': [asin],
            'Resources': [
                'ItemInfo.Title',
                'Offers.Listings.Price',
                'Offers.Listings.Availability.Message',
            ]
        }
        
        payload_str = json.dumps(payload)
        
        # Sign request
        headers = self._sign_request('POST', '/paapi5/getitems', payload_str, timestamp)
        headers['Content-Type'] = 'application/json; charset=utf-8'
        headers['Content-Encoding'] = 'amz-1.0'
        
        # Make request
        url = f"https://{self.endpoint}/paapi5/getitems"
        
        try:
            response = requests.post(url, data=payload_str, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors
            if 'Errors' in data:
                error_msg = data['Errors'][0].get('Message', 'Unknown error')
                print(f"Amazon API Error: {error_msg}")
                return None
            
            # Extract product info
            if 'ItemsResult' in data and 'Items' in data['ItemsResult']:
                items = data['ItemsResult']['Items']
                if items:
                    return self._parse_product_data(items[0])
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Amazon API: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def _parse_product_data(self, item: Dict) -> Dict:
        """Parse product data from API response."""
        asin = item.get('ASIN', '')
        
        # Generate product URL
        domain_map = {
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
        domain = domain_map.get(self.region.upper(), 'amazon.it')
        product_url = f"https://www.{domain}/dp/{asin}"
        
        product_info = {
            'asin': asin,
            'title': '',
            'price': None,
            'currency': 'EUR',
            'availability': 'Unknown',
            'url': product_url,
        }
        
        # Extract title
        if 'ItemInfo' in item and 'Title' in item['ItemInfo']:
            product_info['title'] = item['ItemInfo']['Title'].get('DisplayValue', '')
        
        # Extract price
        if 'Offers' in item and 'Listings' in item['Offers']:
            listings = item['Offers']['Listings']
            if listings:
                listing = listings[0]
                if 'Price' in listing:
                    price_data = listing['Price']
                    if 'Amount' in price_data:
                        product_info['price'] = float(price_data['Amount'])
                    if 'Currency' in price_data:
                        product_info['currency'] = price_data['Currency']
                
                # Extract availability
                if 'Availability' in listing:
                    availability = listing['Availability']
                    if 'Message' in availability:
                        product_info['availability'] = availability['Message']
        
        return product_info
    
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
