"""
Data schemas and type definitions for web2json.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

@dataclass
class HeadingContent:
    """Schema for heading content."""
    type: str = "heading"
    level: int = 1
    text: str = ""

@dataclass
class ParagraphContent:
    """Schema for paragraph content."""
    type: str = "paragraph"
    text: str = ""

@dataclass
class ListItem:
    """Schema for list items."""
    text: str
    type: Optional[str] = None
    list_type: Optional[str] = None
    items: Optional[List['ListItem']] = None

@dataclass
class ListContent:
    """Schema for list content."""
    type: str = "list"
    list_type: str = "unordered"
    level: int = 1
    items: List[ListItem] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []

@dataclass
class BlockquoteContent:
    """Schema for blockquote content."""
    type: str = "blockquote"
    text: str = ""

@dataclass
class SectionContent:
    """Schema for section content."""
    type: str = "section"
    level: int = 1
    content: List[Union[HeadingContent, ParagraphContent, ListContent, BlockquoteContent]] = None

    def __post_init__(self):
        if self.content is None:
            self.content = []

@dataclass
class MetadataSchema:
    """Schema for document metadata."""
    fetched_at: str
    url: str
    preserve_styles: bool = False
    
    @classmethod
    def create(cls, url: str, preserve_styles: bool = False) -> 'MetadataSchema':
        """Create metadata with current timestamp."""
        return cls(
            fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            url=url,
            preserve_styles=preserve_styles
        )

@dataclass
class ContentSchema:
    """Schema for complete document content."""
    title: str
    content: List[Union[HeadingContent, ParagraphContent, ListContent, BlockquoteContent, SectionContent]]
    metadata: MetadataSchema

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary."""
        return {
            "title": self.title,
            "content": [
                (item.__dict__ if hasattr(item, '__dict__') else item)
                for item in self.content
            ],
            "metadata": self.metadata.__dict__
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentSchema':
        """Create schema from dictionary."""
        metadata = MetadataSchema(**data.get('metadata', {}))
        content = []
        
        for item in data.get('content', []):
            if isinstance(item, dict):
                item_type = item.get('type')
                if item_type == 'heading':
                    content.append(HeadingContent(**item))
                elif item_type == 'paragraph':
                    content.append(ParagraphContent(**item))
                elif item_type == 'list':
                    content.append(ListContent(**item))
                elif item_type == 'blockquote':
                    content.append(BlockquoteContent(**item))
                elif item_type == 'section':
                    content.append(SectionContent(**item))
                    
        return cls(
            title=data.get('title', ''),
            content=content,
            metadata=metadata
        )