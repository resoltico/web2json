"""
Fetch module for web2json.

This module provides asynchronous functionality for fetching web content.
"""
import logging
from typing import Optional

import aiohttp

from web2json.utils.errors import FetchError

# Default request timeout in seconds
REQUEST_TIMEOUT = 10

# Default user agent
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)


async def fetch_url(
    url: str,
    timeout: int = REQUEST_TIMEOUT,
    user_agent: Optional[str] = None,
) -> str:
    """Fetch content from a URL asynchronously.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        user_agent: User agent string to use for requests
        
    Returns:
        The fetched content as a string
        
    Raises:
        FetchError: If any error occurs during fetching
    """
    logger = logging.getLogger(__name__)
    
    # Set headers
    headers = {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        # Using aiohttp for async HTTP requests
        async with aiohttp.ClientSession() as session:
            logger.debug(f"Sending GET request to {url}")
            
            async with session.get(
                url,
                headers=headers,
                timeout=timeout,
                raise_for_status=True,
            ) as response:
                logger.debug(f"Received response: HTTP {response.status}")
                content = await response.text()
                logger.debug(f"Fetched {len(content)} bytes")
                return content
                
    except aiohttp.ClientConnectorError:
        logger.error(f"Connection error: Failed to connect to {url}")
        raise FetchError(f"Connection error: Failed to connect to {url}")
        
    except aiohttp.ServerTimeoutError:
        logger.error(f"Timeout error: Request to {url} timed out after {timeout}s")
        raise FetchError(f"Timeout error: Request to {url} timed out after {timeout}s")
        
    except aiohttp.TooManyRedirects:
        logger.error(f"Too many redirects: Maximum redirect limit reached for {url}")
        raise FetchError(f"Too many redirects: Maximum redirect limit reached for {url}")
        
    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP error {e.status}: {e.message}")
        raise FetchError(f"HTTP error {e.status}: {e.message}")
        
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {str(e)}")
        raise FetchError(f"Unexpected error fetching {url}: {str(e)}")
