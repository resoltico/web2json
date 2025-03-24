"""
URL processing and validation functionality.
"""
import logging
import requests
from typing import Optional
from urllib.parse import urlparse
from ..config import (
    MAX_URL_LENGTH,
    REQUEST_TIMEOUT,
    USER_AGENT
)

def validate_url(url: str) -> bool:
    """Validate URL format and scheme."""
    if len(url) > MAX_URL_LENGTH:
        logging.error(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters")
        return False
        
    try:
        result = urlparse(url)
        return all([
            result.scheme in ('http', 'https'),
            result.netloc,
            len(result.netloc) > 0
        ])
    except Exception as e:
        logging.error(f"URL parsing error: {str(e)}")
        return False

def fetch_page(url: str) -> Optional[str]:
    """Fetch webpage content with error handling."""
    headers = {
        "User-Agent": USER_AGENT
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
        
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error for {url}: Check your internet connection")
    except requests.exceptions.Timeout:
        logging.error(f"Timeout error for {url}: Server took too long to respond (>{REQUEST_TIMEOUT}s)")
    except requests.exceptions.TooManyRedirects:
        logging.error(f"Too many redirects for {url}: Check if URL is correct")
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for {url}: Server returned {e.response.status_code}")
    except Exception as e:
        logging.error(f"Unexpected error fetching {url}: {str(e)}")
    
    return None