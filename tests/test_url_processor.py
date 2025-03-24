"""Tests for URL processing functionality."""
import pytest
import requests
import requests_mock
from web2json.core.url_processor import validate_url, fetch_page
from web2json.config import MAX_URL_LENGTH, REQUEST_TIMEOUT

@pytest.fixture
def mock_requests():
    """Fixture to provide a requests_mock instance."""
    with requests_mock.Mocker() as m:
        yield m

def test_validate_url_valid():
    """Test valid URL validation."""
    valid_urls = [
        "https://example.com",
        "http://sub.domain.com",
        "https://example.com/path/to/page",
        "http://example.com/path?param=value",
        "https://example.com:8080/path"
    ]
    for url in valid_urls:
        assert validate_url(url) is True

def test_validate_url_invalid():
    """Test invalid URL validation."""
    invalid_urls = [
        "",
        "not-a-url",
        "ftp://example.com",
        "file:///path/to/file",
        "//example.com",
        f"https://{'x' * MAX_URL_LENGTH}.com"
    ]
    for url in invalid_urls:
        assert validate_url(url) is False

def test_fetch_page_success(mock_requests):
    """Test successful page fetch."""
    url = "https://example.com"
    html_content = "<html><body>Test content</body></html>"
    mock_requests.get(url, text=html_content)
    
    result = fetch_page(url)
    assert result == html_content
    assert mock_requests.called
    assert mock_requests.call_count == 1

def test_fetch_page_connection_error(mock_requests):
    """Test connection error handling."""
    url = "https://example.com"
    mock_requests.get(url, exc=requests.exceptions.ConnectionError)
    
    result = fetch_page(url)
    assert result is None

def test_fetch_page_timeout(mock_requests):
    """Test timeout error handling."""
    url = "https://example.com"
    mock_requests.get(url, exc=requests.exceptions.Timeout)
    
    result = fetch_page(url)
    assert result is None

def test_fetch_page_http_error(mock_requests):
    """Test HTTP error handling."""
    url = "https://example.com"
    error_codes = [400, 403, 404, 500, 502, 503]
    
    for code in error_codes:
        mock_requests.get(url, status_code=code)
        result = fetch_page(url)
        assert result is None

def test_fetch_page_redirect_limit(mock_requests):
    """Test too many redirects handling."""
    url = "https://example.com"
    mock_requests.get(url, exc=requests.exceptions.TooManyRedirects)
    
    result = fetch_page(url)
    assert result is None

def test_fetch_page_request_params(mock_requests):
    """Test request parameters."""
    url = "https://example.com"
    mock_requests.get(url, text="content")
    
    fetch_page(url)
    
    # Verify request had correct timeout and headers
    assert mock_requests.called
    assert "User-Agent" in mock_requests.request_history[0].headers
