"""Parser for Amazon URLs to extract ASIN."""
import re
import logging
from urllib.parse import urlparse, parse_qs
import httpx

logger = logging.getLogger(__name__)


async def extract_asin_with_expansion(text: str) -> str | None:
    """
    Async version that handles short URLs (amzn.eu, amzn.to) by following redirects.
    Expected to be called from async handlers.
    """
    if not text:
        return None
        
    logger.info(f"Extracting ASIN from text: {text[:100]}...")
        
    # First try direct extraction (fastest)
    asin = extract_asin_from_url(text)
    if asin:
        logger.info(f"Found ASIN directly: {asin}")
        return asin
        
    # Find URLs in text
    # More robust regex to find http/https URLs that might include query params
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?'
    urls = re.findall(url_pattern, text)
    
    if not urls:
        logger.warning("No URLs found in message text")
    
    for url in urls:
        # Check if it's a short URL domain
        domain = urlparse(url).netloc.lower()
        if any(d in domain for d in ['amzn.eu', 'amzn.to', 'bit.ly']):
            logger.info(f"Short URL detected: {url} (domain: {domain})")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                # Use a larger timeout and allow more redirects
                async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers=headers) as client:
                    # Some shorteners don't like HEAD, try GET with stream=True to get final URL without downloading full body
                    response = await client.get(url, follow_redirects=True)
                    final_url = str(response.url)
                    
                    logger.info(f"Expanded URL: {url} -> {final_url}")
                    
                    # Extract from expanded URL
                    asin = extract_asin_from_url(final_url)
                    if asin:
                        logger.info(f"Found ASIN after expansion: {asin}")
                        return asin
                    else:
                        logger.warning(f"Could not extract ASIN from expanded URL: {final_url}")
            except Exception as e:
                logger.error(f"Error expanding URL {url}: {e}")
                continue
        else:
            # Not a known shortener, but might still contain ASIN
            asin = extract_asin_from_url(url)
            if asin:
                return asin
                
    return None


def extract_asin_from_url(url: str) -> str | None:
    """
    Extract ASIN from various Amazon URL formats.
    
    Supported formats:
    - https://www.amazon.it/dp/B08N5WRWNW
    - https://www.amazon.it/gp/product/B08N5WRWNW
    - https://www.amazon.it/product-name/dp/B08N5WRWNW/ref=...
    - https://www.amazon.it/dp/B08N5WRWNW/ref=...
    - https://amzn.eu/d/xxxx (if resolved)
    
    Args:
        url: Amazon product URL or text containing it
        
    Returns:
        ASIN string or None if not found
    """
    if not url:
        return None
    
    # Clean URL
    url = url.strip()
    
    # Try to extract ASIN from URL path
    patterns = [
        r'/dp/([A-Z0-9]{10})',  # /dp/B08N5WRWNW
        r'/gp/product/([A-Z0-9]{10})',  # /gp/product/B08N5WRWNW
        r'/product/([A-Z0-9]{10})',  # /product/B08N5WRWNW
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            asin = match.group(1).upper()
            if is_valid_asin(asin):
                return asin
    
    # Try to extract from query parameters
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if 'asin' in query_params:
            asin = query_params['asin'][0].upper()
            if is_valid_asin(asin):
                return asin
            
        # Sometimes ASIN is in parsing query like ?pd_rd_i=B0...
        if 'pd_rd_i' in query_params:
             asin = query_params['pd_rd_i'][0].upper()
             if is_valid_asin(asin):
                 return asin
                  
    except Exception:
        pass
    
    # Try direct ASIN pattern in URL (fallback)
    # Be careful not to match random uppercase strings, search specifically for ASIN-like
    # But ONLY if it looks like an Amazon URL or we are confident
    
    if 'amazon' in url.lower() or 'amzn' in url.lower():
         # Specific pattern for ASIN: usually starts with B0
         asin_match = re.search(r'\b([B][0-9A-Z]{9})\b', url.upper())
         if asin_match:
             potential_asin = asin_match.group(1)
             if is_valid_asin(potential_asin):
                 return potential_asin
                  
    return None


def is_valid_asin(asin: str) -> bool:
    """
    Validate ASIN format.
    
    Args:
        asin: ASIN to validate
        
    Returns:
        True if valid ASIN format
    """
    if not asin:
        return False
    
    if len(asin) != 10:
        return False
    
    if not asin.isalnum():
        return False
    
    return True
