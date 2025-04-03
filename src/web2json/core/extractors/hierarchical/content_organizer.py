"""
Content organizer module for web2json.

This module provides functionality for organizing content elements into a hierarchical structure.
"""
import logging
from typing import List, Dict, Any, Optional

from bs4 import Tag, BeautifulSoup

from web2json.models.content import (
    ContentItem, HeadingContent, ParagraphContent, 
    ListContent, BlockquoteContent, SectionContent,
    CodeContent, TableContent
)
from web2json.core.extractors.base import get_element_text

def sort_blocks_by_position(blocks: List[Tag]) -> List[Tag]:
    """Sort blocks by their position in the document.
    
    Args:
        blocks: List of blocks to sort
        
    Returns:
        Sorted list of blocks
    """
    # Create position index for each block
    def get_position(element):
        # Start at 0
        position = 0
        
        # For each previous sibling, increment position
        for sibling in element.previous_siblings:
            position += 1
        
        # Also consider parent positions to ensure different subtrees maintain order
        parent = element.parent
        parent_multiplier = 1000  # Higher than typical sibling count
        
        while parent:
            parent_position = 0
            for parent_sibling in parent.previous_siblings:
                parent_position += 1
            
            position += parent_position * parent_multiplier
            parent = parent.parent
            parent_multiplier *= 1000  # Increase multiplier for higher level parents
        
        return position
    
    # Get position for each block and sort
    return sorted(blocks, key=get_position)

def organize_hierarchically(blocks: List[Tag], preserve_styles: bool) -> List[ContentItem]:
    """Organize content blocks into a hierarchical structure.
    
    Args:
        blocks: List of content blocks
        preserve_styles: Whether to preserve HTML styles
        
    Returns:
        List of organized content items
    """
    # Initialize result to hold top-level content items
    result = []
    
    # Store processed content fingerprints to prevent duplicates
    processed = set()
    
    # Track sections by level
    sections_stack = []  # Stack of (section object, heading level)
    
    # Process each block in order
    for block in blocks:
        try:
            # Create a fingerprint for deduplication
            # Import here to avoid circular imports
            from web2json.core.extractors.hierarchical.content_scorer import create_content_fingerprint
            
            fingerprint = create_content_fingerprint(block)
            if fingerprint and fingerprint in processed:
                continue
            
            # Mark as processed
            if fingerprint:
                processed.add(fingerprint)
            
            # Handle different block types
            if block.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                # Extract heading level (1-6)
                level = int(block.name[1])
                
                # Create heading content
                heading = HeadingContent(
                    type="heading",
                    level=level,
                    text=get_element_text(block, preserve_styles)
                )
                
                # Create a new section with this heading
                section = SectionContent(
                    type="section",
                    level=level,
                    content=[]
                )
                
                # Close any sections that are lower in hierarchy
                while sections_stack and sections_stack[-1][1] >= level:
                    sections_stack.pop()
                
                # Add this section to its parent (or to result if no parent)
                if sections_stack:
                    parent_section = sections_stack[-1][0]
                    parent_section.content.append(section)
                else:
                    result.append(section)
                
                # Add the heading as first item in section
                section.content.append(heading)
                
                # Add this section to the stack
                sections_stack.append((section, level))
                
            elif block.name == "p":
                # Create paragraph content
                text = get_element_text(block, preserve_styles)
                
                # Skip empty paragraphs
                if not text.strip():
                    continue
                    
                # Create paragraph item
                paragraph = ParagraphContent(
                    type="paragraph",
                    text=text
                )
                
                # Add to current section or result
                if sections_stack:
                    sections_stack[-1][0].content.append(paragraph)
                else:
                    result.append(paragraph)
                    
            elif block.name in ["ul", "ol"]:
                # Import here to avoid circular imports
                from web2json.core.extractors.list_extractor import extract_list_items
                
                # Create list content
                list_type = "ordered" if block.name == "ol" else "unordered"
                list_content = ListContent(
                    type="list",
                    list_type=list_type,
                    items=extract_list_items(block, preserve_styles)
                )
                
                # Add to current section or result
                if sections_stack:
                    sections_stack[-1][0].content.append(list_content)
                else:
                    result.append(list_content)
                    
            elif block.name == "blockquote":
                # Create blockquote content
                blockquote = BlockquoteContent(
                    type="blockquote",
                    text=get_element_text(block, preserve_styles)
                )
                
                # Add to current section or result
                if sections_stack:
                    sections_stack[-1][0].content.append(blockquote)
                else:
                    result.append(blockquote)
                    
            elif block.name == "pre" or (block.name == "div" and block.find("pre")):
                # Import here to avoid circular imports
                from web2json.core.extractors.code_extractor import extract_code_block
                
                # Extract code block as a CodeContent object
                code_content = extract_code_block(block, preserve_styles)
                
                # Add to current section or result
                if sections_stack:
                    sections_stack[-1][0].content.append(code_content)
                else:
                    result.append(code_content)
                    
            elif block.name == "table":
                # Import here to avoid circular imports
                from web2json.core.extractors.table_extractor import extract_table, is_data_table
                
                # Only process actual data tables
                if is_data_table(block):
                    table_content = extract_table(block, preserve_styles)
                    
                    # Add to current section or result
                    if table_content:
                        if sections_stack:
                            sections_stack[-1][0].content.append(table_content)
                        else:
                            result.append(table_content)
                            
        except Exception as e:
            logging.warning(f"Error processing block {block.name}: {str(e)}")
            # Continue with other blocks
    
    # If no organized content (no headings found), just return as flat list
    if not result and blocks:
        # Try a simple extraction of all blocks
        for block in blocks:
            try:
                if block.name == "p":
                    text = get_element_text(block, preserve_styles)
                    if text.strip():
                        result.append(ParagraphContent(type="paragraph", text=text))
                        
                elif block.name in ["ul", "ol"]:
                    # Import here to avoid circular imports
                    from web2json.core.extractors.list_extractor import extract_list_items
                    
                    list_type = "ordered" if block.name == "ol" else "unordered"
                    result.append(ListContent(
                        type="list",
                        list_type=list_type,
                        items=extract_list_items(block, preserve_styles)
                    ))
                    
                elif block.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    level = int(block.name[1])
                    result.append(HeadingContent(
                        type="heading",
                        level=level,
                        text=get_element_text(block, preserve_styles)
                    ))
                    
                elif block.name == "blockquote":
                    result.append(BlockquoteContent(
                        type="blockquote",
                        text=get_element_text(block, preserve_styles)
                    ))
                    
                elif block.name == "pre" or block.find("pre"):
                    # Import here to avoid circular imports
                    from web2json.core.extractors.code_extractor import extract_code_block
                    
                    # Extract as a CodeContent object
                    code_content = extract_code_block(block, preserve_styles)
                    result.append(code_content)
                    
                elif block.name == "table":
                    # Import here to avoid circular imports
                    from web2json.core.extractors.table_extractor import extract_table, is_data_table
                    
                    if is_data_table(block):
                        table_content = extract_table(block, preserve_styles)
                        if table_content:
                            result.append(table_content)
                        
            except Exception as e:
                logging.warning(f"Error in flat extraction: {str(e)}")
    
    return result