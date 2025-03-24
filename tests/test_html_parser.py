"""Tests for HTML parsing functionality."""
import pytest
from bs4 import BeautifulSoup
from web2json.core.html_parser import (
    parse_content,
    extract_heading_level
)
from web2json.core.content_extractor import (
    get_element_text,
    get_list_text_content,
    extract_list_items
)

def test_get_element_text_no_styles():
    """Test text extraction without style preservation."""
    html = """
        <p>Normal text with <b>bold</b> and <i>italic</i> and
        <span class="highlight">highlighted</span> content</p>
    """
    result = get_element_text(html, preserve_styles=False)
    assert result == "Normal text with bold and italic and highlighted content"

def test_get_element_text_with_styles():
    """Test text extraction with style preservation."""
    html = """
        <p>Normal text with <b>bold</b> and <i>italic</i> and
        <span class="highlight">highlighted</span> content</p>
    """
    result = get_element_text(html, preserve_styles=True)
    assert '<b>' in result
    assert '<i>' in result
    assert '<span' not in result  # span is not in STYLE_TAGS

def test_get_list_text_content():
    """Test list item text extraction."""
    html = """
        <li>Main text <b>with bold</b>
            <ul>
                <li>Nested item</li>
            </ul>
        </li>
    """
    soup = BeautifulSoup(html, 'html.parser')
    result = get_list_text_content(soup.li)
    assert result == "Main text with bold"

def test_extract_list_items():
    """Test nested list extraction."""
    html = """
        <ul>
            <li>Item 1
                <ul>
                    <li>Nested 1.1</li>
                    <li>Nested 1.2</li>
                </ul>
            </li>
            <li>Item 2</li>
        </ul>
    """
    soup = BeautifulSoup(html, 'html.parser')
    result = extract_list_items(soup.ul)
    
    assert len(result) == 2
    assert result[0]['text'] == "Item 1"
    assert result[0]['type'] == "sublist"
    assert len(result[0]['items']) == 2
    assert result[1]['text'] == "Item 2"

def test_extract_heading_level():
    """Test heading level extraction."""
    test_cases = [
        ("<h1>Title</h1>", 1),
        ("<h2>Subtitle</h2>", 2),
        ("<h6>Smallest</h6>", 6),
        ("<div>Not a heading</div>", 1),  # Default level
    ]
    
    for html, expected_level in test_cases:
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_heading_level(soup.find())
        assert result == expected_level

def test_parse_content_basic():
    """Test basic content parsing."""
    html = """
        <html>
            <h1>Main Title</h1>
            <p>First paragraph</p>
            <h2>Section</h2>
            <p>Second paragraph</p>
        </html>
    """
    result = parse_content(html, "https://example.com", False)
    
    assert result['title'] == "Main Title"
    assert len(result['content']) > 0
    assert result['metadata']['url'] == "https://example.com"
    assert not result['metadata']['preserve_styles']

def test_parse_content_complex():
    """Test complex content parsing with various elements."""
    html = """
        <html>
            <h1>Article Title</h1>
            <p>Introduction <b>text</b></p>
            <blockquote>Quote text</blockquote>
            <h2>First Section</h2>
            <ul>
                <li>Point 1</li>
                <li>Point 2
                    <ul>
                        <li>Subpoint 2.1</li>
                    </ul>
                </li>
            </ul>
        </html>
    """
    result = parse_content(html, "https://example.com", True)
    
    assert result['title'] == "Article Title"
    content = result['content']
    
    # Verify structure
    types = [item['type'] for item in content]
    assert 'heading' in types
    assert 'paragraph' in types
    assert 'blockquote' in types
    assert 'list' in types
    
    # Verify list structure
    list_items = next(item for item in content if item['type'] == 'list')['items']
    assert len(list_items) == 2
    assert 'sublist' in list_items[1]['type']

def test_parse_content_empty():
    """Test parsing of empty or minimal content."""
    html = "<html><body></body></html>"
    result = parse_content(html, "https://example.com", False)
    
    assert result['title'] == "No Title"
    assert isinstance(result['content'], list)
    assert len(result['content']) == 0

def test_parse_content_metadata():
    """Test metadata handling in content parsing."""
    html = "<html><h1>Title</h1></html>"
    result = parse_content(html, "https://example.com", True)
    
    metadata = result['metadata']
    assert 'fetched_at' in metadata
    assert metadata['url'] == "https://example.com"
    assert metadata['preserve_styles'] is True

def test_parse_content_malformed():
    """Test parsing of malformed HTML."""
    html = """
        <h1>Unclosed Title
        <p>Unclosed Paragraph
        <ul>
            <li>Unclosed List Item
    """
    result = parse_content(html, "https://example.com", False)
    
    assert result['title'] == "Unclosed Title"
    assert len(result['content']) > 0  # Should still extract content