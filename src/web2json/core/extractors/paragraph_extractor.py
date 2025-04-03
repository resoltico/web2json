"""
Paragraph extractor module for web2json.

This module provides functionality for extracting paragraphs from HTML.
"""
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup, Tag

from web2json.models.content import ParagraphContent
from web2json.utils.errors import ExtractError
from web2json.core.extractors.base import get_element_text, is_nested_element

# Tags that generally contain paragraph-like content
PARAGRAPH_TAGS = {"p", "div", "article", "section", "main", "aside", "header", "footer"}

# Tags to ignore when processing paragraphs (these are usually processed separately)
IGNORE_TAGS = {"script", "style", "noscript", "iframe", "form", "nav", "menu"}


def extract_paragraphs(soup: BeautifulSoup, preserve_styles: bool = False) -> List[ParagraphContent]:
    """Extract paragraphs from HTML content.
    
    Args:
        soup: BeautifulSoup object to extract paragraphs from
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of ParagraphContent objects
        
    Raises:
        ExtractError: If paragraph extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        paragraphs = []
        
        # Process explicit paragraph tags first
        for p_tag in soup.find_all("p"):
            # Skip paragraphs that are nested in lists or other structures
            if is_nested_element(p_tag):
                continue
                
            # Skip empty paragraphs
            text = get_element_text(p_tag, preserve_styles)
            if not text.strip():
                continue
                
            # Create paragraph content object
            paragraph = ParagraphContent(
                type="paragraph",
                text=text
            )
            
            paragraphs.append(paragraph)
        
        # Process div elements that likely contain paragraph text
        for div in soup.find_all("div"):
            # Skip divs that are nested in paragraphs or lists
            if (is_nested_element(div) or 
                div.find(["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote"])):
                continue
                
            # Skip divs with certain classes that are not likely to be paragraphs
            if div.get("class") and any(c in ["nav", "menu", "header", "footer", "sidebar"] 
                                       for c in div.get("class")):
                continue
                
            # Extract text and check if it's substantial enough to be a paragraph
            text = get_element_text(div, preserve_styles)
            if text.strip() and len(text.strip()) > 10 and " " in text:
                paragraph = ParagraphContent(
                    type="paragraph",
                    text=text
                )
                paragraphs.append(paragraph)
        
        logger.debug(f"Extracted {len(paragraphs)} paragraphs from document")
        return paragraphs
        
    except Exception as e:
        logger.error(f"Error extracting paragraphs: {str(e)}")
        raise ExtractError(f"Failed to extract paragraphs: {str(e)}")


def extract_text_blocks(element: Tag, preserve_styles: bool = False) -> List[str]:
    """Extract blocks of text from an element, preserving paragraph structure.
    
    Args:
        element: Tag to extract text blocks from
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of text blocks
    """
    blocks = []
    current_block = []
    
    def _process_element(el):
        nonlocal current_block
        
        if el.name == "p":
            # End current block if it exists
            if current_block:
                blocks.append(" ".join(current_block))
                current_block = []
            
            # Add paragraph as a new block
            blocks.append(get_element_text(el, preserve_styles))
            
        elif el.name == "br":
            # End current block if it exists
            if current_block:
                blocks.append(" ".join(current_block))
                current_block = []
                
        elif el.name in IGNORE_TAGS:
            # Skip ignored tags
            pass
            
        elif el.name is None:  # This is a NavigableString
            # Add to current block if non-empty
            text = el.strip()
            if text:
                current_block.append(text)
                
        else:
            # Recursively process children
            for child in el.children:
                _process_element(child)
    
    # Process the element
    _process_element(element)
    
    # Add any remaining block
    if current_block:
        blocks.append(" ".join(current_block))
    
    return blocks


def is_paragraph_element(element: Tag) -> bool:
    """Check if an element is likely a paragraph.
    
    Args:
        element: Element to check
        
    Returns:
        True if the element is likely a paragraph, False otherwise
    """
    # Obvious paragraphs
    if element.name == "p":
        return True
    
    # Divs with paragraph-like content
    if element.name == "div":
        # Skip divs with certain classes
        if element.get("class") and any(c in ["nav", "menu", "sidebar"] for c in element.get("class")):
            return False
            
        # Skip divs with certain structures
        if element.find(["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote"]):
            return False
            
        # Check text content
        text = element.get_text(strip=True)
        return bool(text and len(text) > 10 and " " in text)
    
    return False
