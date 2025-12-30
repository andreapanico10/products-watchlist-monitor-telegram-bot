"""Parser for Amazon URLs to extract ASIN."""
import re
from urllib.parse import urlparse, parse_qs


def extract_asin_from_url(url: str) -> str | None:
    """
    Extract ASIN from various Amazon URL formats.
    
    Supported formats:
    - https://www.amazon.it/dp/B08N5WRWNW
    - https://www.amazon.it/gp/product/B08N5WRWNW
    - https://www.amazon.it/product-name/dp/B08N5WRWNW/ref=...
    - https://www.amazon.it/dp/B08N5WRWNW/ref=...
    
    Args:
        url: Amazon product URL
        
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
    except Exception:
        pass
    
    # Try direct ASIN pattern in URL
    asin_match = re.search(r'\b([A-Z0-9]{10})\b', url.upper())
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
