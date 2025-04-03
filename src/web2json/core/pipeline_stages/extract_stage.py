"""
Extract stage for web2json pipeline.

This module provides the extract stage for extracting structured content from parsed HTML.
"""
import logging
import time
from typing import Dict, Any, List

# Updated import to use the new hierarchical package
from web2json.core.extractors.hierarchical import extract_content_hierarchically
from web2json.core.pipeline_stages.base import run_in_thread
from web2json.utils.errors import ExtractError
from web2json.utils.memory import clear_reference

# Type alias
Context = Dict[str, Any]


class ExtractStage:
    """Pipeline stage for extracting structured content."""
    
    def __init__(self, executor=None):
        """Initialize the extract stage.
        
        Args:
            executor: Optional ThreadPoolExecutor for CPU-bound operations
        """
        self.executor = executor
    
    async def process(self, context: Context) -> Context:
        """Process context by extracting structured content.
        
        Args:
            context: Processing context
            
        Returns:
            Updated context with extracted content
            
        Raises:
            ExtractError: If extraction fails
        """
        soup = context["soup"]
        preserve_styles = context.get("preserve_styles", False)
        logger = logging.getLogger(__name__)
        logger.info("Extracting structured content")
        
        try:
            start_time = time.time()
            
            # Use hierarchical extraction to get structured content
            content = await run_in_thread(
                extract_content_hierarchically, 
                soup, 
                preserve_styles,
                executor=self.executor
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"Extract completed in {elapsed:.2f} seconds")
            
            # Validate extraction results
            if not content:
                logger.warning("Extraction produced no content, attempting fallback extraction")
                
                # Use a direct approach targeting specific elements
                content = await run_in_thread(
                    self._extract_fallback,
                    soup,
                    preserve_styles,
                    executor=self.executor
                )
                
                if not content:
                    logger.error("Fallback extraction failed to produce content")
                    raise ExtractError("Failed to extract any content from the document")
            
            # Store extracted content in context
            context["content"] = content
            context["extract_time"] = elapsed
            
            # Log extraction stats
            self._log_extraction_stats(content)
            
            # Clear soup reference from memory as it's no longer needed
            clear_reference(context, "soup")
            
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            # Ensure we clean up memory even on error
            clear_reference(context, "soup")
            raise ExtractError(f"Failed to extract content: {str(e)}")
        
        return context
    
    def _extract_fallback(self, soup, preserve_styles):
        """Fallback extraction method for when hierarchical extraction fails.
        
        This method tries a more direct approach targeting specific elements.
        
        Args:
            soup: BeautifulSoup object
            preserve_styles: Whether to preserve HTML styles
            
        Returns:
            List of content items
        """
        from web2json.models.content import ParagraphContent
        
        logger = logging.getLogger(__name__)
        logger.debug("Performing fallback extraction")
        
        content = []
        
        # Get all paragraphs directly
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                content.append(ParagraphContent(type="paragraph", text=text))
        
        # Get all headings directly
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            from web2json.models.content import HeadingContent
            level = int(h.name[1])
            text = h.get_text(strip=True)
            if text:
                content.append(HeadingContent(type="heading", level=level, text=text))
        
        # Get code blocks directly
        for pre in soup.find_all("pre"):
            from web2json.core.extractors.code_extractor import extract_code_block
            code_content = extract_code_block(pre, preserve_styles)
            content.append(code_content)
        
        logger.debug(f"Fallback extraction found {len(content)} content items")
        return content
    
    def _log_extraction_stats(self, content):
        """Log statistics about extracted content.
        
        Args:
            content: Extracted content
        """
        logger = logging.getLogger(__name__)
        
        # Count items by type
        type_counts = {}
        total_text_length = 0
        
        def count_items(items):
            nonlocal total_text_length
            for item in items:
                # Handle both dictionary and object access
                if isinstance(item, dict):
                    # Dictionary access
                    item_type = item.get("type", "unknown")
                    type_counts[item_type] = type_counts.get(item_type, 0) + 1
                    
                    # Count text length for text-based content
                    if "text" in item:
                        total_text_length += len(item["text"])
                    
                    # Recurse into sections
                    if item_type == "section" and "content" in item:
                        count_items(item["content"])
                else:
                    # Object access
                    try:
                        # Try to get the type attribute directly
                        item_type = getattr(item, "type", "unknown")
                        type_counts[item_type] = type_counts.get(item_type, 0) + 1
                        
                        # Try to get the text attribute for text length
                        if hasattr(item, "text"):
                            text = getattr(item, "text", "")
                            total_text_length += len(text)
                        
                        # Recurse into sections
                        if item_type == "section" and hasattr(item, "content"):
                            count_items(item.content)
                    except Exception as e:
                        logger.debug(f"Error processing item in stats: {e}")
        
        try:
            count_items(content)
            
            # Log the stats
            logger.info(f"Extracted {len(content)} top-level content items")
            logger.info(f"Total text length: {total_text_length} characters")
            logger.info(f"Content type distribution: {type_counts}")
        except Exception as e:
            # Don't let stats logging failure affect the extraction
            logger.debug(f"Error logging extraction stats: {e}")
