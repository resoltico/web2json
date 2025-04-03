"""
Fetch stage for web2json pipeline.

This module provides the fetch stage for retrieving web content.
"""
import logging
import time
from typing import Dict, Any

from web2json.core.fetch import fetch_url
from web2json.utils.errors import FetchError
from web2json.utils.url import validate_url

# Type alias
Context = Dict[str, Any]


class FetchStage:
    """Pipeline stage for fetching web content."""
    
    async def process(self, context: Context) -> Context:
        """Process context by fetching web content.
        
        Args:
            context: Processing context
            
        Returns:
            Updated context with HTML content
            
        Raises:
            FetchError: If fetching fails
        """
        url = context["url"]
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching content from URL: {url}")
        
        # Validate URL before attempting to fetch
        if not validate_url(url):
            raise FetchError(f"Invalid URL format: {url}")
        
        timeout = context.get("timeout", 60)
        user_agent = context.get("user_agent", None)
        
        start_time = time.time()
        
        try:
            # Fetch HTML content from URL
            html_content = await fetch_url(
                url=url,
                timeout=timeout,
                user_agent=user_agent
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"Fetch completed in {elapsed:.2f} seconds")
            
            # Store results in context
            context["html_content"] = html_content
            context["content_length"] = len(html_content)
            context["fetch_time"] = elapsed
            
        except FetchError as e:
            # Re-raise FetchError
            logger.error(f"Fetch error for {url}: {str(e)}")
            raise
            
        except Exception as e:
            # Convert other exceptions to FetchError
            logger.error(f"Unexpected error during fetch for {url}: {str(e)}")
            raise FetchError(f"Unexpected error during fetch: {str(e)}")
        
        return context
