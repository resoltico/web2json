"""Tests for file handling functionality."""
import pytest
import os
from pathlib import Path
from web2json.utils.file_handler import (
    expand_path,
    is_safe_path,
    sanitize_filename,
    validate_output_path,
    generate_filename
)
from web2json.exceptions import PathError
from web2json.config import MAX_FILENAME_LENGTH

def test_expand_path():
    """Test path expansion."""
    # Test home directory expansion
    home = os.path.expanduser("~")
    assert expand_path("~/test") == os.path.join(home, "test")
    
    # Test environment variable expansion
    os.environ["TEST_DIR"] = "/test/dir"
    assert expand_path("$TEST_DIR/file") == "/test/dir/file"
    
    # Test relative path normalization
    assert expand_path("./test/../file") == "file"
    
    with pytest.raises(PathError):
        expand_path(None)

def test_is_safe_path():
    """Test path safety validation."""
    base_dir = "/base/dir"
    
    # Test safe paths
    assert is_safe_path(base_dir, "/base/dir/file.txt")
    assert is_safe_path(base_dir, "/base/dir/subdir/file.txt")
    
    # Test unsafe paths
    assert not is_safe_path(base_dir, "/other/dir/file.txt")
    assert not is_safe_path(base_dir, "/base/dir/../other/file.txt")
    assert not is_safe_path(base_dir, None)

def test_sanitize_filename():
    """Test filename sanitization."""
    test_cases = [
        ("normal.txt", "normal.txt"),
        ("file with spaces.txt", "file_with_spaces.txt"),
        ("../path/file.txt", "path_file.txt"),
        ("file@#$%.txt", "file.txt"),
        ("über.txt", "uber.txt"),
        ("", ""),
        ("..hiddenfile", "hiddenfile"),
        ("filename.with.many.dots.txt", "filename_with_many_dots.txt")
    ]
    
    for input_name, expected in test_cases:
        assert sanitize_filename(input_name) == expected

def test_validate_output_path(tmp_path):
    """Test output path validation."""
    # Test valid paths
    valid_path = os.path.join(tmp_path, "test.json")
    assert validate_output_path(tmp_path, "test.json") == valid_path
    
    # Test nested directory creation
    nested_dir = os.path.join(tmp_path, "subdir")
    assert validate_output_path(nested_dir, "test.json")
    assert os.path.exists(nested_dir)
    
    # Test long filename
    long_name = "x" * (MAX_FILENAME_LENGTH + 1)
    with pytest.raises(ValueError):
        validate_output_path(tmp_path, long_name)
    
    # Test invalid directory (should raise an error)
    invalid_dir = "/nonexistent/dir"
    with pytest.raises(Exception):
        validate_output_path(invalid_dir, "test.json")

def test_generate_filename():
    """Test filename generation."""
    # Test with URL
    url = "https://example.com/path/to/page"
    dir_path, filename = generate_filename(url, "output")
    assert os.path.isabs(dir_path)  # Ensure absolute path
    assert "example_com" in filename
    assert "path_to_page" in filename
    assert filename.endswith(".json")
    
    # Test with custom name
    dir_path, filename = generate_filename(url, "output", "custom")
    assert filename == "custom.json"
    
    # Test with custom path
    dir_path, filename = generate_filename(url, "output", "subdir/custom")
    assert os.path.isabs(dir_path)
    assert dir_path.endswith("subdir")
    assert filename == "custom.json"
    
    # Test with absolute path
    abs_path = os.path.abspath("/test/path/file")
    dir_path, filename = generate_filename(url, "output", abs_path)
    assert os.path.isabs(dir_path)
    assert filename == "file.json"
    
    # Test with long URL path
    long_url = f"https://example.com/{'x' * 100}"
    dir_path, filename = generate_filename(long_url, "output")
    assert len(filename) <= MAX_FILENAME_LENGTH

def test_generate_filename_errors():
    """Test filename generation error cases."""
    url = "https://example.com"
    
    # Test with invalid custom name (e.g., using unsafe path traversal)
    with pytest.raises(PathError):
        generate_filename(url, "output", "../../escape")
    
    # Test with empty values
    with pytest.raises(PathError):
        generate_filename("", "output")

    # Test with None values
    with pytest.raises(PathError):
        generate_filename(None, "output")

    with pytest.raises(PathError):
        generate_filename(url, None)