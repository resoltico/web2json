"""
Parse module for web2json.

This module provides functionality for parsing HTML content into a structured form.
"""
import logging
from typing import Tuple, Dict, Optional

from bs4 import BeautifulSoup, NavigableString

from web2json.utils.errors import ParseError


def parse_html(html_content: str, parser: str = "lxml") -> Tuple[BeautifulSoup, str, Dict[str, str]]:
    """Parse HTML content and extract basic metadata.
    
    Args:
        html_content: Raw HTML content to parse
        parser: BeautifulSoup parser to use (default: lxml for memory efficiency)
        
    Returns:
        Tuple of (BeautifulSoup object, title, metadata)
        
    Raises:
        ParseError: If parsing fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Parse HTML content using lxml for better memory efficiency
        soup = BeautifulSoup(html_content, parser)
        
        # Extract title
        title = extract_title(soup)
        
        # Extract metadata
        meta_tags = extract_meta_tags(soup)
        
        return soup, title, meta_tags
        
    except Exception as e:
        logger.error(f"Failed to parse HTML content: {str(e)}")
        raise ParseError(f"Failed to parse HTML content: {str(e)}")


def extract_title(soup: BeautifulSoup) -> str:
    """Extract title from parsed HTML.
    
    Attempts to extract title from:
    1. First h1 element
    2. OG title meta tag
    3. Title tag
    4. Default to "No Title"
    
    Args:
        soup: Parsed BeautifulSoup object
        
    Returns:
        Extracted title or default
    """
    logger = logging.getLogger(__name__)
    
    # Try to get title from first h1
    title_elem = soup.find("h1")
    if title_elem:
        title = ''.join(
            text for text in title_elem.contents 
            if isinstance(text, NavigableString)
        ).strip()
        if title:
            logger.debug(f"Found title in h1: {title}")
            return title
    
    # Try to get title from og:title meta tag
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        logger.debug(f"Found title in og:title: {og_title['content']}")
        return og_title["content"]
    
    # Try to get title from title tag
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        logger.debug(f"Found title in title tag: {title_tag.string.strip()}")
        return title_tag.string.strip()
    
    logger.debug("No title found, using default")
    return "No Title"


def extract_meta_tags(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract metadata from HTML meta tags.
    
    Args:
        soup: Parsed BeautifulSoup object
        
    Returns:
        Dictionary of metadata key-value pairs
    """
    meta_tags = {}
    
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if name and content:
            meta_tags[name] = content
    
    return meta_tags


def extract_heading_level(element: BeautifulSoup) -> int:
    """Extract numeric heading level from h1-h6 tags.
    
    Args:
        element: Heading element
        
    Returns:
        Heading level (1-6)
    """
    try:
        return int(element.name[1])
    except (IndexError, ValueError):
        return 1