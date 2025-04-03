"""
Content finder module for web2json.

This module provides functionality for finding content elements in HTML.
"""
import logging
import re
from typing import List, Set, Optional

from bs4 import BeautifulSoup, Tag, NavigableString

# Constants from the original file
CONTENT_CONTAINERS = {
    "article", "main", "div", "section", "content", "post", "entry", 
    "blog-post", "page-content", "post-content", "entry-content", "article-content",
    "body-content", "page-body", "prose", "markdown", "md-content", "site-content"
}

STRUCTURAL_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "blockquote", "pre", "ul", "ol", "dl", "table",
    "article", "section", "main"
}

EXCLUDE_TAGS = {
    "nav", "header", "footer", "aside", "sidebar", "advertisement", "menu",
    "banner", "ad", "widget", "comment", "comments", "related", "share",
    "social", "toolbar", "navigation", "breadcrumb", "pagination", "search"
}

MIN_TEXT_LENGTH = 30
MIN_PARAGRAPH_LENGTH = 20

CONTENT_CLASS_PATTERNS = [
    r'(^|\s)(article|blog|post|entry|content|main|body|text|page)(\s|$)',
    r'(^|\s)(prose|markdown|md|doc|document|story|narrative)(\s|$)',
    r'(^|\s)(sl-markdown-content)(\s|$)',
]

NON_CONTENT_PATTERNS = [
    r'(^|\s)(sidebar|widget|banner|ad|advertisement|promo|popup)(\s|$)',
    r'(^|\s)(menu|nav|footer|header|copyright|social|share|toolbar)(\s|$)',
    r'(^|\s)(comment|related|recommended|popular|trending)(\s|$)'
]

def find_main_content_elements(soup: BeautifulSoup) -> List[Tag]:
    """Find elements likely to contain the main content.
    
    This function uses multiple strategies to identify content containers:
    1. Common HTML5 semantic elements
    2. Elements with content-related class/id names
    3. Elements with high text-to-tag ratios
    4. Content containers specific to common frameworks/CMS
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        List of elements likely to contain main content
    """
    potential_elements = []
    
    # Strategy 1: Look for semantic HTML5 elements
    semantic_elements = soup.find_all(['article', 'main', 'section'])
    potential_elements.extend(semantic_elements)
    
    # Strategy 2: Look for elements with content-related classes
    # First compile all patterns
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in CONTENT_CLASS_PATTERNS]
    
    for element in soup.find_all(True):
        # Skip elements that are already in our list
        if element in potential_elements:
            continue
            
        # Check class attribute
        if element.get('class'):
            class_str = ' '.join(element.get('class', []))
            for pattern in compiled_patterns:
                if pattern.search(class_str):
                    potential_elements.append(element)
                    break
        
        # Check id attribute
        if element.get('id'):
            id_str = element.get('id', '')
            for pattern in compiled_patterns:
                if pattern.search(id_str):
                    potential_elements.append(element)
                    break
    
    # Strategy 3: Look for specific content containers used by common frameworks
    # Starlight framework
    starlight_content = soup.select('.sl-markdown-content, .prose')
    potential_elements.extend(starlight_content)
    
    # WordPress and other common CMS
    cms_content = soup.select('.entry-content, .post-content, .article-body, .content-area')
    potential_elements.extend(cms_content)
    
    # Medium-like platforms
    medium_content = soup.select('article section, [role="article"]')
    potential_elements.extend(medium_content)
    
    # Documentation sites
    docs_content = soup.select('.documentation, .docs-content, .markdown-body')
    potential_elements.extend(docs_content)
    
    # Strategy 4: Analyze text-to-tag ratio for generic <div> elements
    for div in soup.find_all('div'):
        # Skip small divs and already processed divs
        if div in potential_elements or len(div.get_text(strip=True)) < 200:
            continue
            
        # Calculate text-to-tag ratio
        text_length = len(div.get_text(strip=True))
        tags_count = len(div.find_all(True))
        
        if tags_count > 0:
            ratio = text_length / tags_count
            # High ratio indicates content-heavy element
            if ratio > 10:
                potential_elements.append(div)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_elements = []
    for element in potential_elements:
        element_id = id(element)
        if element_id not in seen:
            seen.add(element_id)
            unique_elements.append(element)
    
    return unique_elements

def is_likely_non_content(element: Tag) -> bool:
    """Check if an element is likely to be navigation, footer, etc. rather than content.
    
    Args:
        element: Element to check
        
    Returns:
        True if likely non-content
    """
    # Check element name
    if element.name in ['nav', 'footer', 'header']:
        return True
    
    # Check class and id attributes
    for attr in ['class', 'id']:
        if element.get(attr):
            attr_value = ' '.join(element.get(attr)) if isinstance(element.get(attr), list) else element.get(attr)
            
            # Check against non-content patterns
            for pattern in NON_CONTENT_PATTERNS:
                if re.search(pattern, attr_value, re.IGNORECASE):
                    return True
                    
    # Check role attribute
    if element.get('role') in ['navigation', 'banner', 'contentinfo']:
        return True
        
    return False

def extract_content_blocks(element: Tag) -> List[Tag]:
    """Extract content blocks from an element, focusing on structural elements.
    
    Args:
        element: Element to extract blocks from
        
    Returns:
        List of block-level elements
    """
    blocks = []
    
    # Process direct block-level children
    for child in element.children:
        if isinstance(child, NavigableString):
            # Skip empty strings
            if not child.strip():
                continue
                
            # Wrap text nodes in a paragraph if they're substantial
            if len(child.strip()) > MIN_PARAGRAPH_LENGTH:
                p = BeautifulSoup(f"<p>{child}</p>", 'html.parser').p
                blocks.append(p)
                
        elif isinstance(child, Tag):
            if child.name in STRUCTURAL_TAGS:
                # Skip elements that might be non-content
                if is_likely_non_content(child):
                    continue
                
                blocks.append(child)
            elif child.name not in ['script', 'style', 'meta', 'link', 'noscript', 'svg', 'button', 'input']:
                # Recursively extract blocks from container elements
                nested_blocks = extract_content_blocks(child)
                blocks.extend(nested_blocks)
    
    # If we didn't find blocks directly, look deeper
    if not blocks:
        # Look for direct structural elements anywhere in the subtree
        for structural in element.find_all(STRUCTURAL_TAGS):
            # Skip elements already processed
            if any(structural is block or structural in block for block in blocks):
                continue
                
            # Skip tiny elements and likely non-content
            if len(structural.get_text(strip=True)) < MIN_TEXT_LENGTH and structural.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                continue
                
            if is_likely_non_content(structural):
                continue
                
            blocks.append(structural)
    
    return blocks

def extract_content_aggressively(soup: BeautifulSoup) -> List[Tag]:
    """Extract content aggressively, finding any potential content elements.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        List of potential content elements
    """
    blocks = []
    
    # Look for headings with content
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        # Skip tiny headings
        if len(heading.get_text(strip=True)) < 10:
            continue
        
        # Skip headings in non-content areas
        if is_likely_non_content(heading):
            continue
            
        blocks.append(heading)
        
        # Look for content following headings
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Stop at the next heading
                    break
                    
                if sibling.name in ['p', 'ul', 'ol', 'blockquote', 'pre']:
                    blocks.append(sibling)
    
    # Look for substantial paragraphs
    for p in soup.find_all('p'):
        # Skip tiny paragraphs
        if len(p.get_text(strip=True)) < MIN_PARAGRAPH_LENGTH:
            continue
            
        # Skip paragraphs in non-content areas
        if is_likely_non_content(p):
            continue
            
        blocks.append(p)
    
    # Look for lists with substantial content
    for lst in soup.find_all(['ul', 'ol']):
        # Skip empty lists
        if not lst.find_all('li'):
            continue
            
        # Skip lists in non-content areas
        if is_likely_non_content(lst):
            continue
            
        blocks.append(lst)
    
    # Look for code blocks
    for pre in soup.find_all(['pre', 'code']):
        # Skip tiny code blocks
        if len(pre.get_text(strip=True)) < 10:
            continue
        
        blocks.append(pre)
    
    # Look for tables
    for table in soup.find_all('table'):
        # Import here to avoid circular imports
        from web2json.core.extractors.table_extractor import is_data_table
        
        if is_data_table(table) and not is_likely_non_content(table):
            blocks.append(table)
    
    return blocks