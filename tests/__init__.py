"""
Test suite for web2json package.

This package contains tests for all core functionality including:
- URL processing and validation
- HTML parsing and content extraction
- JSON conversion and file handling
- CLI interface
"""

import pytest
import os
import tempfile
from typing import Generator
from pathlib import Path

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for test file operations."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

@pytest.fixture
def sample_html() -> str:
    """Provide sample HTML content for testing."""
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <p>Test paragraph</p>
            <ul>
                <li>List item 1</li>
                <li>List item 2</li>
            </ul>
        </body>
    </html>
    """

@pytest.fixture
def sample_json_data() -> dict:
    """Provide sample structured data for testing."""
    return {
        "title": "Test Page",
        "content": [
            {
                "type": "heading",
                "level": 1,
                "text": "Main Title"
            },
            {
                "type": "paragraph",
                "text": "Test paragraph"
            }
        ],
        "metadata": {
            "fetched_at": "2025-01-18 22:18:18",
            "url": "https://example.com",
            "preserve_styles": False
        }
    }