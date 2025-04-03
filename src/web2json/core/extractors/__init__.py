"""
Extractors package for web2json.

This package contains modules for extracting different types of content from HTML.
"""
from web2json.core.extractors.base import (
    get_element_text,
    is_nested_element,
    get_element_position,
    STYLE_TAGS,
    STRUCTURAL_TAGS
)

from web2json.core.extractors.heading_extractor import (
    extract_headings,
    find_heading_sections,
    extract_heading_tree
)

from web2json.core.extractors.paragraph_extractor import (
    extract_paragraphs,
    extract_text_blocks,
    is_paragraph_element
)

from web2json.core.extractors.list_extractor import (
    extract_lists,
    extract_list_items,
    get_list_text_content,
    detect_list_structure
)

from web2json.core.extractors.code_extractor import (
    extract_code_block,
    extract_code_caption,
    detect_code_language,
    extract_formatted_code
)

from web2json.core.extractors.table_extractor import (
    extract_tables,
    extract_table,
    detect_table_structure,
    is_data_table
)

# Import from the new hierarchical package
from web2json.core.extractors.hierarchical import (
    extract_content_hierarchically,
    find_main_content_elements,
    score_content_element,
    organize_hierarchically
)

__all__ = [
    # Base extractor
    'get_element_text',
    'is_nested_element',
    'get_element_position',
    'STYLE_TAGS',
    'STRUCTURAL_TAGS',
    
    # Heading extractor
    'extract_headings',
    'find_heading_sections',
    'extract_heading_tree',
    
    # Paragraph extractor
    'extract_paragraphs',
    'extract_text_blocks',
    'is_paragraph_element',
    
    # List extractor
    'extract_lists',
    'extract_list_items',
    'get_list_text_content',
    'detect_list_structure',
    
    # Code extractor
    'extract_code_block',
    'extract_code_caption',
    'detect_code_language',
    'extract_formatted_code',
    
    # Table extractor
    'extract_tables',
    'extract_table',
    'detect_table_structure',
    'is_data_table',
    
    # Hierarchical extractor
    'extract_content_hierarchically',
    'find_main_content_elements',
    'score_content_element',
    'organize_hierarchically'
]