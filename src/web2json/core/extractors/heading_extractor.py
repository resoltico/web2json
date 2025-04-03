"""
Heading extractor module for web2json.

This module provides functionality for extracting headings from HTML.
"""
import logging
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup, Tag

from web2json.models.content import HeadingContent
from web2json.utils.errors import ExtractError
from web2json.core.extractors.base import get_element_text, is_nested_element

# Define heading element tag names
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def extract_headings(soup: BeautifulSoup, preserve_styles: bool = False) -> List[HeadingContent]:
    """Extract all headings from HTML content in order of appearance.
    
    Args:
        soup: BeautifulSoup object to extract headings from
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of HeadingContent objects
        
    Raises:
        ExtractError: If heading extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        headings = []
        
        # Process headings in document order
        for heading_tag in soup.find_all(HEADING_TAGS):
            # Skip headings that are nested in lists or other structures
            if is_nested_element(heading_tag):
                continue
                
            # Get heading level (h1 = 1, h2 = 2, etc.)
            level = int(heading_tag.name[1])
            
            # Extract text content
            text = get_element_text(heading_tag, preserve_styles)
            
            # Create heading content object
            heading = HeadingContent(
                type="heading",
                level=level,
                text=text
            )
            
            headings.append(heading)
        
        logger.debug(f"Extracted {len(headings)} headings from document")
        return headings
        
    except Exception as e:
        logger.error(f"Error extracting headings: {str(e)}")
        raise ExtractError(f"Failed to extract headings: {str(e)}")


def find_heading_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Find sections of content defined by headings.
    
    This function identifies where each heading starts and what content belongs to it.
    
    Args:
        soup: BeautifulSoup object to analyze
        
    Returns:
        List of section dictionaries with heading and elements
        
    Raises:
        ExtractError: If section analysis fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        sections = []
        current_heading = None
        current_elements = []
        
        # Get all top-level elements (direct children of body or article)
        content_container = soup.find(["article", "main"]) or soup.body
        if not content_container:
            logger.warning("No content container found, using whole document")
            content_container = soup
        
        # Process elements in document order
        for element in content_container.find_all(recursive=False):
            # If element is a heading, start a new section
            if element.name in HEADING_TAGS:
                # If we already have a heading, add the current section
                if current_heading:
                    sections.append({
                        "heading": current_heading,
                        "elements": current_elements
                    })
                
                # Start a new section
                current_heading = element
                current_elements = []
            else:
                # Add element to current section
                current_elements.append(element)
        
        # Add the last section
        if current_heading:
            sections.append({
                "heading": current_heading,
                "elements": current_elements
            })
        
        logger.debug(f"Found {len(sections)} heading-based sections")
        return sections
        
    except Exception as e:
        logger.error(f"Error finding heading sections: {str(e)}")
        raise ExtractError(f"Failed to find heading sections: {str(e)}")


def extract_heading_tree(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract a hierarchical tree of headings showing document structure.
    
    Args:
        soup: BeautifulSoup object to analyze
        
    Returns:
        Dictionary representing the document's heading structure
        
    Raises:
        ExtractError: If heading analysis fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Find all headings
        headings = soup.find_all(HEADING_TAGS)
        
        # Initialize heading tree
        heading_tree = {
            "title": _get_document_title(soup),
            "children": []
        }
        
        # Stack to track the current path in the heading hierarchy
        # Each item is (heading node, level)
        stack = [(heading_tree, 0)]
        
        # Process headings in document order
        for heading in headings:
            level = int(heading.name[1])
            text = heading.get_text(strip=True)
            
            # Create new heading node
            new_node = {
                "text": text,
                "level": level,
                "id": _generate_heading_id(text),
                "children": []
            }
            
            # Find the appropriate parent for this heading
            while stack[-1][1] >= level:
                stack.pop()
                
            # Add new heading to its parent
            parent, _ = stack[-1]
            parent["children"].append(new_node)
            
            # Add new heading to stack
            stack.append((new_node, level))
        
        logger.debug(f"Extracted heading tree with {len(heading_tree['children'])} top-level sections")
        return heading_tree
        
    except Exception as e:
        logger.error(f"Error extracting heading tree: {str(e)}")
        raise ExtractError(f"Failed to extract heading tree: {str(e)}")


def _get_document_title(soup: BeautifulSoup) -> str:
    """Extract the document title.
    
    Args:
        soup: BeautifulSoup object to extract title from
        
    Returns:
        Document title
    """
    # Try title tag first
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    
    # Try h1 if no title tag
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    
    # Default title
    return "Untitled Document"


def _generate_heading_id(text: str) -> str:
    """Generate an ID from heading text.
    
    Args:
        text: Heading text
        
    Returns:
        ID string suitable for anchors
    """
    # Convert to lowercase and replace spaces with hyphens
    id_text = text.lower().strip()
    id_text = id_text.replace(" ", "-")
    
    # Remove special characters
    id_text = ''.join(c for c in id_text if c.isalnum() or c == '-')
    
    # Ensure id starts with a letter
    if id_text and not id_text[0].isalpha():
        id_text = "section-" + id_text
    
    # Fallback for empty id
    if not id_text:
        id_text = "section"
        
    return id_text
