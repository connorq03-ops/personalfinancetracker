"""
Extract simplified merchant names from transaction descriptions.
"""
import re


# Known merchant mappings (description pattern -> clean name)
MERCHANT_MAPPINGS = {
    'spotify': 'Spotify',
    'netflix': 'Netflix',
    'amazon': 'Amazon',
    'amz*': 'Amazon',
    'apple.com/bill': 'Apple',
    'uber *trip': 'Uber',
    'uber *eats': 'Uber Eats',
    'lyft': 'Lyft',
    'doordash': 'DoorDash',
    'grubhub': 'Grubhub',
    'starbucks': 'Starbucks',
    'houndstooth': 'Houndstooth Coffee',
    'la colombe': 'La Colombe',
    'h-e-b': 'H-E-B',
    'heb ': 'H-E-B',
    'whole foods': 'Whole Foods',
    'trader joe': 'Trader Joe\'s',
    'target': 'Target',
    'walmart': 'Walmart',
    'costco': 'Costco',
    'cvs': 'CVS',
    'walgreens': 'Walgreens',
    'shell': 'Shell',
    'chevron': 'Chevron',
    'exxon': 'Exxon',
    'venmo': 'Venmo',
    'paypal': 'PayPal',
    'zelle': 'Zelle',
    'chase credit': 'Chase CC Payment',
    'robinhood card': 'Robinhood CC',
    'fid bkg svc': 'Fidelity',
    'acorns': 'Acorns',
    'ymca': 'YMCA',
    'nintendo': 'Nintendo',
    'microsoft': 'Microsoft',
    'hulu': 'Hulu',
    'disney+': 'Disney+',
    'hbo': 'HBO',
    'chipotle': 'Chipotle',
    'panera': 'Panera',
    'chick-fil-a': 'Chick-fil-A',
    'mcdonald': 'McDonald\'s',
    'taco bell': 'Taco Bell',
    'whataburger': 'Whataburger',
    'truist mortg': 'Truist Mortgage',
    'one gas': 'ONE Gas',
    'city of austin': 'City of Austin',
    'att des:payment': 'AT&T',
    'comcast': 'Comcast',
    'spectrum': 'Spectrum',
    'southwest': 'Southwest Airlines',
    'delta': 'Delta Airlines',
    'united': 'United Airlines',
    'american air': 'American Airlines',
    'airbnb': 'Airbnb',
    'marriott': 'Marriott',
    'hilton': 'Hilton',
    'bkofamerica atm': 'BoA ATM',
    'wire type:': 'Wire Transfer',
    'austin fc': 'Austin FC',
    'levy@': 'Austin FC',
    'jabbrrbox': 'Jabbrrbox',
    'tonal systems': 'Tonal',
    'stubhub': 'StubHub',
    'tst*': 'Restaurant',
    'glf*': 'Golf',
    'sp ': 'Shopify',
    'sq *': 'Square',
    'home depot': 'Home Depot',
    'surf thru': 'Surf Thru',
    'fellow products': 'Fellow',
    'harveypenick': 'Harvey Penick Golf',
}


def extract_merchant_name(description):
    """
    Extract a clean, simplified merchant name from a transaction description.
    
    Examples:
        "1013 SPOTIFY 877-778-1161 NY" -> "Spotify"
        "1010 LEVY@ 2AUSTIN FC AUSTIN TX" -> "Austin FC"
        "MOBILE PURCHASE 0925 SQ *LA COLOMBE - LAMAR Austin" -> "La Colombe"
    """
    if not description:
        return "Unknown"
    
    desc_lower = description.lower()
    
    # Check known mappings first
    for pattern, merchant in MERCHANT_MAPPINGS.items():
        if pattern in desc_lower:
            return merchant
    
    # Try to extract merchant from common patterns
    cleaned = _clean_description(description)
    
    return cleaned if cleaned else "Unknown"


def _clean_description(description):
    """Clean and simplify a transaction description."""
    # Remove common prefixes
    prefixes = [
        r'^\d{4}\s+',  # Date prefix like "1013 "
        r'^MOBILE PURCHASE\s+\d+\s+',
        r'^PURCHASE\s+',
        r'^CHECKCARD\s+\d+\s+',
        r'^POS\s+',
        r'^SQ \*',  # Square
        r'^TST\*',  # Toast
    ]
    
    text = description
    for prefix in prefixes:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)
    
    # Remove trailing location info (city, state, zip, phone)
    # Pattern: city STATE or city STATE ZIP or phone numbers
    text = re.sub(r'\s+\d{3}[-.]?\d{3}[-.]?\d{4}.*$', '', text)  # Phone numbers
    text = re.sub(r'\s+[A-Z]{2}\s*\d{5}(-\d{4})?$', '', text)  # State + ZIP
    text = re.sub(r'\s+[A-Z]{2}$', '', text)  # Just state
    text = re.sub(r'\s+\d{10,}$', '', text)  # Long numbers at end
    
    # Remove common suffixes
    text = re.sub(r'\s+(AUSTIN|DALLAS|HOUSTON|TX|CA|NY|WA)\s*$', '', text, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    text = ' '.join(text.split())
    
    # Title case if all caps
    if text.isupper():
        text = text.title()
    
    # Limit length
    if len(text) > 30:
        text = text[:27] + '...'
    
    return text.strip()


# Add as a Jinja2 filter
def init_app(app):
    """Register the merchant extractor as a Jinja2 filter."""
    app.jinja_env.filters['merchant'] = extract_merchant_name
