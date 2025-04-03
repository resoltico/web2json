"""
Hierarchical extractor module for web2json.

This module provides the main functionality for extracting content in a hierarchical structure.
"""
import logging
from typing import List

from bs4 import BeautifulSoup

from web2json.models.content import ContentItem
from web2json.utils.errors import ExtractError

# Import components from the hierarchical extractor package
from web2json.core.extractors.hierarchical.content_finder import (
    find_main_content_elements,
    extract_content_blocks,
    extract_content_aggressively
)
from web2json.core.extractors.hierarchical.content_scorer import (
    score_content_element,
    get_content_text_length,
    create_content_fingerprint
)
from web2json.core.extractors.hierarchical.content_organizer import (
    organize_hierarchically,
    sort_blocks_by_position
)

# Constants
MIN_TEXT_LENGTH = 30

def extract_content_hierarchically(soup: BeautifulSoup, preserve_styles: bool = False) -> List[ContentItem]:
    """Extract structured content from HTML in a hierarchical manner.
    
    Args:
        soup: BeautifulSoup object representing the parsed HTML
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of structured content items organized hierarchically
        
    Raises:
        ExtractError: If extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # First, try to get the main content area
        content_elements = find_main_content_elements(soup)
        logger.debug(f"Found {len(content_elements)} potential content elements")
        
        if not content_elements:
            logger.warning("Could not identify main content elements, falling back to whole document")
            content_elements = [soup.body or soup]
        
        # Filter for elements with substantial textual content
        content_elements = [element for element in content_elements 
                           if get_content_text_length(element) > MIN_TEXT_LENGTH]
        
        # Get the element with the highest content score
        scored_elements = [(element, score_content_element(element)) for element in content_elements]
        scored_elements.sort(key=lambda x: x[1], reverse=True)
        
        # Process the top content elements until we have substantial content
        processed_blocks = []
        processed_fingerprints = set()
        content_sufficient = False
        
        for element, score in scored_elements:
            logger.debug(f"Processing content element with score {score}")
            
            # Extract blocks from this element
            blocks = extract_content_blocks(element)
            
            # Deduplicate blocks
            filtered_blocks = []
            for block in blocks:
                fingerprint = create_content_fingerprint(block)
                if fingerprint and fingerprint not in processed_fingerprints:
                    processed_fingerprints.add(fingerprint)
                    filtered_blocks.append(block)
            
            processed_blocks.extend(filtered_blocks)
            
            # Check if we now have sufficient content
            total_text = sum(len(block.get_text(strip=True)) for block in processed_blocks)
            if total_text > 500 and len(processed_blocks) > 5:
                content_sufficient = True
                break
        
        # If still no substantial content, try aggressive extraction
        if not content_sufficient:
            logger.warning("Insufficient content found, trying aggressive extraction")
            aggressive_blocks = extract_content_aggressively(soup)
            
            # Deduplicate these blocks as well
            for block in aggressive_blocks:
                fingerprint = create_content_fingerprint(block)
                if fingerprint and fingerprint not in processed_fingerprints:
                    processed_fingerprints.add(fingerprint)
                    processed_blocks.append(block)
        
        # Sort blocks to maintain document order
        processed_blocks = sort_blocks_by_position(processed_blocks)
        
        # Organize content into hierarchical structure
        hierarchical_content = organize_hierarchically(processed_blocks, preserve_styles)
        
        logger.info(f"Extracted {len(hierarchical_content)} top-level content items")
        return hierarchical_content
        
    except Exception as e:
        logger.error(f"Error extracting hierarchical content: {str(e)}")
        raise ExtractError(f"Failed to extract hierarchical content: {str(e)}")
