"""
Content scorer module for web2json.

This module provides functionality for scoring content elements based on relevance.
"""
import logging
import re
from typing import Optional

from bs4 import Tag

# Constants from the original file
MIN_TEXT_LENGTH = 30

# Content class patterns for scoring
CONTENT_CLASS_PATTERNS = [
    r'(^|\s)(article|blog|post|entry|content|main|body|text|page)(\s|$)',
    r'(^|\s)(prose|markdown|md|doc|document|story|narrative)(\s|$)',
    r'(^|\s)(sl-markdown-content)(\s|$)',
]

# Patterns indicating non-content areas
NON_CONTENT_PATTERNS = [
    r'(^|\s)(sidebar|widget|banner|ad|advertisement|promo|popup)(\s|$)',
    r'(^|\s)(menu|nav|footer|header|copyright|social|share|toolbar)(\s|$)',
    r'(^|\s)(comment|related|recommended|popular|trending)(\s|$)'
]

def score_content_element(element: Tag) -> float:
    """Calculate a relevance score for a content element.
    
    Higher scores indicate better content candidates.
    
    Args:
        element: Element to score
        
    Returns:
        Relevance score
    """
    score = 0.0
    
    # Get text content
    text_content = element.get_text(strip=True)
    text_length = len(text_content)
    
    # Base score on text length
    score += min(text_length / 100, 10)  # Cap at 10 points
    
    # Bonus for semantic elements
    if element.name in ['article', 'main', 'section']:
        score += 5
    
    # Bonus for content-related class names
    if element.get('class'):
        class_str = ' '.join(element.get('class', []))
        for pattern in CONTENT_CLASS_PATTERNS:
            if re.search(pattern, class_str, re.IGNORECASE):
                score += 3
                break
    
    # Bonus for content-related id
    if element.get('id'):
        id_str = element.get('id')
        for pattern in CONTENT_CLASS_PATTERNS:
            if re.search(pattern, id_str, re.IGNORECASE):
                score += 3
                break
    
    # Penalty for likely non-content areas
    for pattern in NON_CONTENT_PATTERNS:
        class_str = ' '.join(element.get('class', []))
        id_str = element.get('id', '')
        
        if re.search(pattern, class_str, re.IGNORECASE) or re.search(pattern, id_str, re.IGNORECASE):
            score -= 5
    
    # Bonus for heading elements
    score += len(element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])) * 2
    
    # Bonus for paragraph density
    paragraphs = element.find_all('p')
    if len(paragraphs) > 0:
        # Calculate average paragraph length
        p_text_length = sum(len(p.get_text(strip=True)) for p in paragraphs)
        avg_p_length = p_text_length / len(paragraphs) if len(paragraphs) > 0 else 0
        
        # Bonus for reasonable paragraph length (suggesting real content)
        if avg_p_length > 40:
            score += 3
        
        # Bonus for multiple paragraphs
        score += min(len(paragraphs) / 2, 5)  # Cap at 5 points
    
    # Bonus for presence of lists, blockquotes, and other content elements
    score += len(element.find_all(['ul', 'ol', 'blockquote', 'pre', 'code', 'table'])) * 1.5
    
    # Penalty for too many links (possibly navigation)
    links = element.find_all('a')
    if links:
        link_text = sum(len(a.get_text(strip=True)) for a in links)
        link_ratio = link_text / text_length if text_length > 0 else 1
        
        if link_ratio > 0.5:  # More than half the text is in links
            score -= 4
    
    return max(score, 0)  # Ensure score is not negative

def get_content_text_length(element: Tag) -> int:
    """Get the total text length of an element, excluding scripts, styles, etc.
    
    Args:
        element: Element to analyze
        
    Returns:
        Text length in characters
    """
    # Clone the element to avoid modifying the original
    elem_copy = element
    
    # Remove script, style tags from the copy
    for tag in elem_copy.find_all(['script', 'style', 'noscript']):
        tag.decompose()
    
    return len(elem_copy.get_text(strip=True))

def create_content_fingerprint(element: Tag) -> Optional[str]:
    """Create a fingerprint for an element to detect duplicates.
    
    Args:
        element: Element to fingerprint
        
    Returns:
        Fingerprint string or None if element is too small
    """
    # Ignore tiny elements
    text = element.get_text(strip=True)
    if len(text) < 15:
        return None
    
    # Create fingerprint from element name, class, and text
    element_type = element.name
    
    # Get first and last 20 chars of text for the fingerprint
    text_start = text[:20].strip()
    text_end = text[-20:].strip() if len(text) > 40 else ""
    
    # Include tag name and some text in fingerprint
    fingerprint = f"{element_type}:{text_start}:{text_end}"
    
    return fingerprint