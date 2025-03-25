"""
Parse stage for the web2json pipeline.

This stage parses HTML content into a structured form for extraction.
"""
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, NavigableString
from .base import PipelineStage
from ....exceptions import ParseError

class HTMLParser:
    """HTML parser for web content."""
    
    def __init__(self, parser: str = 'html.parser'):
        """Initialize the HTML parser.
        
        Args:
            parser: BeautifulSoup parser to use
        """
        self.parser_type = parser
    
    def parse(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content into a BeautifulSoup object.
        
        Args:
            html_content: Raw HTML content to parse
            
        Returns:
            Parsed BeautifulSoup object
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            return BeautifulSoup(html_content, self.parser_type)
        except Exception as e:
            raise ParseError(f"Failed to parse HTML content: {str(e)}")
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from parsed HTML.
        
        Attempts to extract title from:
        1. First h1 element
        2. OG title meta tag
        3. Title tag
        4. Default to "No Title"
        
        Args:
            soup: Parsed BeautifulSoup object
            
        Returns:
            Extracted title or default
        """
        # Try to get title from first h1
        title_elem = soup.find("h1")
        if title_elem:
            title = ''.join(
                text for text in title_elem.contents 
                if isinstance(text, NavigableString)
            ).strip()
            if title:
                return title
        
        # Try to get title from og:title meta tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]
        
        # Try to get title from title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # Default title
        return "No Title"

class ParseStage(PipelineStage):
    """Pipeline stage for parsing HTML content.
    
    This stage takes HTML content from the context, parses it into
    a BeautifulSoup object, extracts basic metadata, and adds them
    to the context for the next stage.
    """
    
    def __init__(self, html_parser: Optional[HTMLParser] = None):
        """Initialize the parse stage.
        
        Args:
            html_parser: HTML parser to use
        """
        super().__init__()
        self.html_parser = html_parser or HTMLParser()
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context by parsing HTML content.
        
        Args:
            context: Pipeline context containing 'html_content'
            
        Returns:
            Updated context with 'soup' and basic metadata
            
        Raises:
            ValueError: If HTML content is missing from context
            ParseError: If parsing fails
        """
        self.validate_context(context, ['html_content', 'url'])
        
        html_content = context['html_content']
        self.logger.info("Parsing HTML content")
        
        try:
            # Parse the HTML
            soup = self.html_parser.parse(html_content)
            context['soup'] = soup
            
            # Extract basic metadata
            title = self.html_parser.extract_title(soup)
            context['title'] = title
            
            # Extract other metadata
            meta_tags = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property")
                content = meta.get("content")
                if name and content:
                    meta_tags[name] = content
            
            context['meta_tags'] = meta_tags
            
            self.logger.info(f"Successfully parsed HTML, title: {title}")
            return context
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            raise
