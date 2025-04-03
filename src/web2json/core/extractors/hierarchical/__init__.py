"""
Hierarchical extractor package for web2json.

This package provides functionality for extracting content in a hierarchical structure
that reflects the document's semantic organization.
"""
from web2json.core.extractors.hierarchical.extractor import extract_content_hierarchically
from web2json.core.extractors.hierarchical.content_finder import (
    find_main_content_elements,
    extract_content_blocks,
    extract_content_aggressively,
    is_likely_non_content
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

# Re-export main function and key supporting functions 
# to maintain backward compatibility
__all__ = [
    'extract_content_hierarchically',
    'find_main_content_elements',
    'score_content_element',
    'organize_hierarchically',
    'extract_content_blocks',
    'extract_content_aggressively',
    'sort_blocks_by_position',
    'get_content_text_length',
    'create_content_fingerprint',
    'is_likely_non_content'
]
