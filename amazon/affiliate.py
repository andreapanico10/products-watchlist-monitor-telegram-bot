"""Generate Amazon affiliate links."""
from config.settings import settings


def generate_affiliate_link(asin: str, region: str = None) -> str:
    """
    Generate Amazon affiliate link with affiliate tag.
    
    Args:
        asin: Product ASIN
        region: Amazon region (IT, US, UK, etc.). Defaults to settings.AMAZON_REGION
        
    Returns:
        Affiliate link URL
    """
    if not asin:
        raise ValueError("ASIN is required")
    
    region = region or settings.AMAZON_REGION
    
    # Map region to domain
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
    
    domain = domain_map.get(region.upper(), 'amazon.it')
    affiliate_tag = settings.AMAZON_AFFILIATE_TAG
    
    if affiliate_tag:
        return f"https://www.{domain}/dp/{asin}?tag={affiliate_tag}"
    else:
        return f"https://www.{domain}/dp/{asin}"


def generate_base_affiliate_link(region: str = None) -> str:
    """
    Generate base Amazon homepage affiliate link with affiliate tag.
    This link redirects to Amazon homepage and any purchase made after clicking
    will generate affiliate commissions.
    
    Args:
        region: Amazon region (IT, US, UK, etc.). Defaults to settings.AMAZON_REGION
        
    Returns:
        Base affiliate link URL (homepage with tag)
    """
    region = region or settings.AMAZON_REGION
    
    # Map region to domain
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
    
    domain = domain_map.get(region.upper(), 'amazon.it')
    affiliate_tag = settings.AMAZON_AFFILIATE_TAG
    
    if affiliate_tag:
        return f"https://www.{domain}/?tag={affiliate_tag}"
    else:
        return f"https://www.{domain}/"
