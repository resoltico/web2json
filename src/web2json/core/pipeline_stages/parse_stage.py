"""
Parse stage for web2json pipeline.

This module provides the parse stage for converting HTML content to a BeautifulSoup object.
"""
import logging
import time
from typing import Dict, Any

from web2json.core.parse import parse_html
from web2json.core.pipeline_stages.base import run_in_thread
from web2json.utils.errors import ParseError
from web2json.utils.memory import clear_reference

# Type alias
Context = Dict[str, Any]


class ParseStage:
    """Pipeline stage for parsing HTML content."""
    
    def __init__(self, executor=None):
        """Initialize the parse stage.
        
        Args:
            executor: Optional ThreadPoolExecutor for CPU-bound operations
        """
        self.executor = executor
    
    async def process(self, context: Context) -> Context:
        """Process context by parsing HTML content.
        
        Args:
            context: Processing context
            
        Returns:
            Updated context with parsed content
            
        Raises:
            ParseError: If parsing fails
        """
        html_content = context["html_content"]
        logger = logging.getLogger(__name__)
        logger.info("Parsing HTML content")
        
        try:
            start_time = time.time()
            
            # Use thread pool for CPU-intensive parsing
            soup, title, meta_tags = await run_in_thread(
                parse_html, html_content, executor=self.executor
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"Parse completed in {elapsed:.2f} seconds")
            
            # Clear HTML content from memory as it's no longer needed
            clear_reference(context, "html_content")
            
            # Store results in context
            context["soup"] = soup
            context["title"] = title
            context["meta_tags"] = meta_tags
            context["parse_time"] = elapsed
            
            # Extract important metadata for later use
            description = meta_tags.get("description") or meta_tags.get("og:description")
            if description:
                context["description"] = description
            
            # Store content type if available
            content_type = meta_tags.get("content-type")
            if content_type:
                context["content_type"] = content_type
            
        except Exception as e:
            logger.error(f"Error parsing HTML content: {str(e)}")
            # Ensure we clean up memory even on error
            clear_reference(context, "html_content")
            raise ParseError(f"Failed to parse HTML content: {str(e)}")
        
        return context
