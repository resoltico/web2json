"""
Code block extractor module for web2json.

This module provides functionality for extracting and formatting code blocks
with proper preservation of line breaks and separation of captions.
"""
import logging
import re
from typing import Dict, Any, Optional, List, Union

from bs4 import BeautifulSoup, Tag, NavigableString

from web2json.utils.errors import ExtractError
from web2json.core.extractors.base import get_element_text
from web2json.models.content import CodeContent

# Tags that indicate a code block
CODE_TAGS = {'pre', 'code'}

# Tags that indicate a code block caption or title
CAPTION_TAGS = {'figcaption', 'caption', 'div', 'span'}

# Define a pattern to detect terminal window headers or titles
TERMINAL_WINDOW_PATTERN = re.compile(r'terminal(\s+window)?', re.IGNORECASE)

# Common language class patterns
LANGUAGE_CLASS_PATTERNS = [
    # Common language class prefixes
    re.compile(r'language-(\w+)'),
    re.compile(r'lang-(\w+)'),
    re.compile(r'syntax-(\w+)'),
    re.compile(r'brush:\s*(\w+)'),
    re.compile(r'(\w+)-syntax'),
    
    # Common highlighter-specific patterns
    re.compile(r'html|css|js|javascript|python|ruby|php|java|go|rust|cpp|csharp|shell|bash|sql', re.IGNORECASE),
]


def extract_code_block(element: Tag, preserve_styles: bool = False) -> CodeContent:
    """Extract a code block with proper formatting and caption handling.
    
    Args:
        element: HTML element containing a code block
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        CodeContent object representing the code block
        
    Raises:
        ExtractError: If extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Find the actual code element
        code_element = element
        
        # If we received a container, find the pre or code element within it
        if element.name not in CODE_TAGS:
            # First try pre with code inside (standard pattern)
            pre_element = element.find("pre")
            if pre_element:
                code_element = pre_element
            else:
                # Try for code element directly
                code_element = element.find("code") or element
        
        # Extract caption if present in the container or nearby
        caption = extract_code_caption(element)
            
        # Extract language information
        language = detect_code_language(code_element)
            
        # Extract formatted code content
        text_content = extract_formatted_code(code_element)
        
        # Make sure we have some content
        if not text_content.strip():
            raise ValueError("Code block is empty")
        
        # Create the CodeContent object directly
        return CodeContent(
            type="code_block",
            text=text_content,
            language=language,
            caption=caption
        )
        
    except Exception as e:
        logger.error(f"Error extracting code block: {str(e)}")
        # Fallback to simpler extraction
        try:
            return CodeContent(
                type="code_block",
                text=element.get_text(strip=False),
                language=detect_code_language(element),
                caption=None
            )
        except Exception:
            # Ultimate fallback
            return CodeContent(
                type="code_block",
                text="Error extracting code",
                language=None,
                caption=None
            )


def extract_code_caption(element: Tag) -> Optional[str]:
    """Extract caption from a code block container.
    
    This function searches in multiple locations and patterns to find captions:
    1. Direct figcaption within the element or its parent
    2. Caption-like elements with specific classes
    3. Screen reader elements that describe the code
    4. Title attributes
    5. Code-specific container classes
    
    Args:
        element: HTML element that might contain a code caption
        
    Returns:
        Caption text if found, otherwise None
    """
    # Check for figcaption element within the container
    figcaption = element.find('figcaption')
    if figcaption:
        return figcaption.get_text(strip=True)
    
    # Check parent for figcaption if this is a pre/code inside a figure
    parent = element.parent
    if parent and parent.name == 'figure':
        parent_caption = parent.find('figcaption')
        if parent_caption:
            return parent_caption.get_text(strip=True)
    
    # Check for elements with caption/title classes or data attributes
    caption_patterns = [
        'caption', 'title', 'header', 'heading', 'label',
        'code-label', 'code-title', 'code-caption', 'snippet-title'
    ]
    
    for pattern in caption_patterns:
        # Check for elements with specific class names
        caption_el = element.find(class_=lambda c: c and pattern in c.lower())
        if caption_el:
            return caption_el.get_text(strip=True)
            
        # Check for data attributes
        caption_el = element.find(attrs=lambda a: any(
            f'data-{pattern}' in k.lower() for k in a.keys() if isinstance(k, str)
        ))
        if caption_el:
            return caption_el.get_text(strip=True)
    
    # Check for siblings that might be captions
    prev_sibling = element.find_previous_sibling()
    if prev_sibling and prev_sibling.name in ['div', 'p', 'span', 'h3', 'h4', 'h5', 'h6']:
        text = prev_sibling.get_text(strip=True)
        if text and len(text) < 100:  # Captions are typically short
            for pattern in caption_patterns:
                if pattern in prev_sibling.get('class', []) or pattern in prev_sibling.get('id', ''):
                    return text
    
    # Check for screen reader elements that might contain captions
    sr_patterns = ['sr-only', 'visually-hidden', 'screen-reader', 'sr']
    for pattern in sr_patterns:
        sr_element = element.find(class_=lambda c: c and pattern in str(c))
        if sr_element:
            text = sr_element.get_text(strip=True)
            # Check if it looks like a terminal window description
            if TERMINAL_WINDOW_PATTERN.search(text):
                return text
    
    # Look for title attribute on the element or its parent
    if element.has_attr('title') and element['title'].strip():
        return element['title'].strip()
        
    if parent and parent.has_attr('title') and parent['title'].strip():
        return parent['title'].strip()
    
    # Check for aria-label which might contain caption info
    if element.has_attr('aria-label') and element['aria-label'].strip():
        return element['aria-label'].strip()
    
    # Look for specific terminal window containers in Starlight docs
    terminal_patterns = ['frame is-terminal', 'terminal-window', 'command-line']
    for pattern in terminal_patterns:
        if element.get('class') and any(pattern in c for c in element.get('class', [])):
            return "Terminal window"
            
        if parent and parent.get('class') and any(pattern in c for c in parent.get('class', [])):
            return "Terminal window"
    
    return None


def detect_code_language(element: Tag) -> Optional[str]:
    """Attempt to detect the programming language of a code block.
    
    This function checks various common patterns for language specification:
    1. Class attributes with language prefixes
    2. Data attributes that specify languages
    3. Content analysis for language-specific patterns
    
    Args:
        element: HTML element containing code
        
    Returns:
        Detected language if found, otherwise None
    """
    # Check element's class for language indicators
    if element.has_attr('class'):
        classes = element['class'] if isinstance(element['class'], list) else [element['class']]
        
        # Check against language patterns
        for class_name in classes:
            if not class_name or not isinstance(class_name, str):
                continue
                
            # Check common language class patterns
            for pattern in LANGUAGE_CLASS_PATTERNS:
                match = pattern.search(class_name)
                if match:
                    # If there's a capture group, use it as the language
                    if match.groups():
                        return match.group(1).lower()
                    # Otherwise use the full match
                    return match.group(0).lower()
    
    # Check parent's class for language indicators
    parent = element.parent
    if parent and parent.has_attr('class'):
        classes = parent['class'] if isinstance(parent['class'], list) else [parent['class']]
        
        for class_name in classes:
            if not class_name or not isinstance(class_name, str):
                continue
                
            for pattern in LANGUAGE_CLASS_PATTERNS:
                match = pattern.search(class_name)
                if match:
                    if match.groups():
                        return match.group(1).lower()
                    return match.group(0).lower()
    
    # Check for data-language attribute
    for attr_name in ['data-language', 'data-lang', 'data-code-language']:
        if element.has_attr(attr_name):
            return element[attr_name].lower()
            
        if parent and parent.has_attr(attr_name):
            return parent[attr_name].lower()
    
    # Check for bash/shell indicators in code content
    text = element.get_text()
    if text.strip().startswith('$') or text.strip().startswith('#!'):
        # Lines starting with $ or #! are likely shell
        return 'bash'
        
    # Look for language-specific patterns in text content
    if re.search(r'^\s*(import|from)\s+\w+\s+import', text, re.MULTILINE):
        return 'python'
        
    if re.search(r'^\s*(function|const|let|var)\s+\w+', text, re.MULTILINE):
        return 'javascript'
        
    if re.search(r'^\s*(class|public|private)\s+\w+', text, re.MULTILINE):
        # Could be Java, C#, etc. - default to generic
        return 'code'
        
    if re.search(r'^\s*<\?php', text, re.MULTILINE):
        return 'php'
        
    # Default to code if we can't determine language
    return None


def extract_formatted_code(element: Tag) -> str:
    """Extract code content with preserved formatting.
    
    This function preserves whitespace, indentation, and line breaks that
    are semantically important in code blocks.
    
    Args:
        element: HTML element containing code
        
    Returns:
        Formatted code content with preserved whitespace
    """
    # Look for nested code tag if we're in a pre tag
    code_tag = element.find('code') if element.name == 'pre' else element
    
    # If no code tag found, use the current element
    if not code_tag:
        code_tag = element
    
    # Get the text content, preserving whitespace
    # Instead of using get_text(), we'll access the raw content
    # to better preserve formatting
    raw_text = ""
    
    try:
        # Method 1: Use recursion to build the text content
        def extract_text(node):
            nonlocal raw_text
            if isinstance(node, NavigableString):
                raw_text += node
            elif node.name == 'br':
                raw_text += '\n'
            elif node.name not in ['script', 'style']:
                for child in node.children:
                    extract_text(child)
        
        extract_text(code_tag)
        
        # If raw_text is empty, fallback to get_text
        if not raw_text:
            raw_text = code_tag.get_text()
    except Exception:
        # Fallback to get_text if there's an error
        raw_text = code_tag.get_text()
    
    # Normalize line breaks
    content = re.sub(r'\r\n|\r', '\n', raw_text)
    
    # Remove common leading whitespace (dedent)
    lines = content.split('\n')
    if lines:
        # Find common leading whitespace, ignoring empty lines
        common_indent = None
        for line in lines:
            if not line.strip():  # Skip empty lines
                continue
            indent = len(line) - len(line.lstrip())
            if common_indent is None or indent < common_indent:
                common_indent = indent
        
        # Remove common leading whitespace
        if common_indent and common_indent > 0:
            formatted_lines = []
            for line in lines:
                if line.strip():  # Only process non-empty lines
                    formatted_lines.append(line[min(common_indent, len(line) - len(line.lstrip())):])
                else:
                    formatted_lines.append(line)
            content = '\n'.join(formatted_lines)
    
    # Trim leading/trailing blank lines
    content = content.strip('\n')
    
    return content
