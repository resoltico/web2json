"""
Fetch stage for the web2json pipeline.

This stage fetches HTML content from a URL.
"""
from typing import Dict, Any, Optional
import requests
from .base import PipelineStage
from ....exceptions import FetchError

class HTTPClient:
    """HTTP client for fetching web content."""
    
    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        """Initialize the HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            user_agent: User-agent string to use for requests
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
    
    def fetch(self, url: str) -> str:
        """Fetch content from a URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            The fetched content as a string
            
        Raises:
            FetchError: If fetching fails
        """
        headers = {
            "User-Agent": self.user_agent
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.ConnectionError:
            raise FetchError(f"Connection error: Failed to connect to {url}")
        except requests.exceptions.Timeout:
            raise FetchError(f"Timeout error: Request to {url} timed out after {self.timeout}s")
        except requests.exceptions.TooManyRedirects:
            raise FetchError(f"Too many redirects: Maximum redirect limit reached for {url}")
        except requests.exceptions.HTTPError as e:
            raise FetchError(f"HTTP error {e.response.status_code}: {e}")
        except Exception as e:
            raise FetchError(f"Unexpected error fetching {url}: {str(e)}")

class FetchStage(PipelineStage):
    """Pipeline stage for fetching web content.
    
    This stage takes a URL from the context, fetches the content,
    and adds it to the context for the next stage.
    """
    
    def __init__(self, http_client: Optional[HTTPClient] = None):
        """Initialize the fetch stage.
        
        Args:
            http_client: HTTP client to use for fetching content
        """
        super().__init__()
        self.http_client = http_client or HTTPClient()
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context by fetching web content.
        
        Args:
            context: Pipeline context containing 'url'
            
        Returns:
            Updated context with 'html_content'
            
        Raises:
            ValueError: If URL is missing from context
            FetchError: If fetching fails
        """
        self.validate_context(context, ['url'])
        
        url = context['url']
        self.logger.info(f"Fetching content from URL: {url}")
        
        try:
            html_content = self.http_client.fetch(url)
            
            # Update the context with the fetched content
            context['html_content'] = html_content
            context['content_length'] = len(html_content)
            self.logger.info(f"Successfully fetched {context['content_length']} bytes from {url}")
            
            return context
        except Exception as e:
            self.logger.error(f"Error fetching content: {str(e)}")
            raise
