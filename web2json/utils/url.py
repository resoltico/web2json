"""
URL utilities for web2json.
"""
import logging
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional
from ..config import MAX_URL_LENGTH

def validate_url(url: str) -> bool:
    """Validate URL format and scheme.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid
    """
    if not url:
        logging.error("URL cannot be empty")
        return False
        
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

def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize URL, optionally resolving against a base URL.
    
    Args:
        url: URL to normalize
        base_url: Base URL to resolve against
        
    Returns:
        Normalized URL
        
    Raises:
        ValueError: If URL is invalid
    """
    if not validate_url(url) and not base_url:
        raise ValueError(f"Invalid URL: {url}")
        
    try:
        parsed = urlparse(url)
        
        # If URL is relative and we have a base URL, resolve it
        if not parsed.netloc and base_url:
            return urljoin(base_url, url)
            
        # Normalize the URL components
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        # Remove trailing slash if present and there's a path
        if normalized.endswith('/') and len(parsed.path) > 1:
            normalized = normalized[:-1]
            
        return normalized
    except Exception as e:
        raise ValueError(f"Failed to normalize URL {url}: {str(e)}")

def extract_domain(url: str) -> str:
    """Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
        
    Raises:
        ValueError: If URL is invalid
    """
    if not validate_url(url):
        raise ValueError(f"Invalid URL: {url}")
        
    parsed = urlparse(url)
    return parsed.netloc
