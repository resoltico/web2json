"""Tests for JSON conversion functionality."""
import pytest
import json
import os
from datetime import datetime
from web2json.core.json_converter import (
    save_json,
    load_json,
    validate_json_data,
    format_json_data,
    JSONEncoder
)
from web2json.exceptions import ConversionError

@pytest.fixture
def valid_data():
    return {
        "title": "Test Title",
        "content": [
            {
                "type": "heading",
                "level": 1,
                "text": "Main Heading"
            },
            {
                "type": "paragraph",
                "text": "Test paragraph"
            }
        ],
        "metadata": {
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": "https://example.com",
            "preserve_styles": False
        }
    }

def test_validate_json_data(valid_data):
    """Test JSON data validation."""
    assert validate_json_data(valid_data) is True
    
    # Test missing required fields
    invalid_data = valid_data.copy()
    del invalid_data["title"]
    assert validate_json_data(invalid_data) is False
    
    # Test missing metadata fields
    invalid_data = valid_data.copy()
    del invalid_data["metadata"]["url"]
    assert validate_json_data(invalid_data) is False
    
    # Test invalid content type
    invalid_data = valid_data.copy()
    invalid_data["content"] = "not a list"
    assert validate_json_data(invalid_data) is False

def test_format_json_data(valid_data):
    """Test JSON data formatting."""
    # Add some None values
    valid_data["content"].append(None)
    valid_data["metadata"]["empty"] = None
    
    formatted = format_json_data(valid_data)
    
    assert None not in formatted["content"]
    assert "empty" not in formatted["metadata"]
    
    with pytest.raises(ConversionError):
        format_json_data("not a dict")

def test_json_encoder():
    """Test custom JSON encoder."""
    encoder = JSONEncoder()
    
    # Test datetime encoding
    dt = datetime.now()
    assert encoder.default(dt) == dt.isoformat()
    
    # Test fallback
    with pytest.raises(TypeError):
        encoder.default(object())

def test_save_json(tmp_path, valid_data):
    """Test JSON file saving."""
    # Test successful save
    result = save_json(valid_data, tmp_path, "test.json")
    assert result is True
    
    filepath = os.path.join(tmp_path, "test.json")
    assert os.path.exists(filepath)
    
    # Verify saved content
    with open(filepath, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
        assert saved_data["title"] == valid_data["title"]
        assert len(saved_data["content"]) == len(valid_data["content"])
    
    # Test invalid data
    invalid_data = valid_data.copy()
    del invalid_data["title"]
    result = save_json(invalid_data, tmp_path, "invalid.json")
    assert result is False
    
    # Test invalid path
    result = save_json(valid_data, "/nonexistent/path", "test.json")
    assert result is False

def test_load_json(tmp_path, valid_data):
    """Test JSON file loading."""
    filepath = os.path.join(tmp_path, "test.json")
    
    # Save test data
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(valid_data, f)
    
    # Test successful load
    loaded_data = load_json(filepath)
    assert loaded_data is not None
    assert loaded_data["title"] == valid_data["title"]
    
    # Test invalid JSON
    with open(filepath, 'w') as f:
        f.write("invalid json")
    assert load_json(filepath) is None
    
    # Test nonexistent file
    assert load_json("/nonexistent/file.json") is None
    
    # Test with Path object
    from pathlib import Path
    assert load_json(Path(filepath)) is None  # File still contains invalid JSON

def test_json_indentation(tmp_path, valid_data):
    """Test JSON formatting and indentation."""
    filepath = os.path.join(tmp_path, "test.json")
    
    # Save with default indentation
    save_json(valid_data, tmp_path, "test.json")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        
        # Check indentation structure
        assert any(line.startswith('  "') for line in lines)  # 2-space indent
        assert any(line.startswith('    "') for line in lines)  # 4-space indent