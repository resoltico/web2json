"""
Content models module for web2json.

This module defines the Pydantic models for content items in the document.
"""
from typing import List, Optional, Union, Literal

from pydantic import BaseModel, Field


class BaseContentItem(BaseModel):
    """Base class for all content items."""
    
    type: str = Field(..., description="Type of content item")


class HeadingContent(BaseContentItem):
    """Content model for headings."""
    
    type: Literal["heading"] = Field("heading", description="Type of content item")
    level: int = Field(1, description="Heading level (1-6)", ge=1, le=6)
    text: str = Field("", description="Heading text")


class ParagraphContent(BaseContentItem):
    """Content model for paragraphs."""
    
    type: Literal["paragraph"] = Field("paragraph", description="Type of content item")
    text: str = Field("", description="Paragraph text")


class ListItem(BaseModel):
    """Model for list items, supporting nested lists."""
    
    text: str = Field(..., description="List item text")
    type: Optional[Literal["sublist"]] = Field(None, description="Type of list item, if nested")
    list_type: Optional[Literal["ordered", "unordered"]] = Field(None, description="Type of nested list")
    items: Optional[List["ListItem"]] = Field(None, description="Nested list items")


# Create recursive model for ListItem
ListItem.model_rebuild()


class ListContent(BaseContentItem):
    """Content model for lists."""
    
    type: Literal["list"] = Field("list", description="Type of content item")
    list_type: Literal["ordered", "unordered"] = Field("unordered", description="Type of list")
    items: List[ListItem] = Field(default_factory=list, description="List items")


class BlockquoteContent(BaseContentItem):
    """Content model for blockquotes."""
    
    type: Literal["blockquote"] = Field("blockquote", description="Type of content item")
    text: str = Field("", description="Blockquote text")


class SectionContent(BaseContentItem):
    """Content model for document sections."""
    
    type: Literal["section"] = Field("section", description="Type of content item")
    level: int = Field(1, description="Section level")
    content: List[Union[
        HeadingContent, 
        ParagraphContent, 
        ListContent, 
        BlockquoteContent
    ]] = Field(default_factory=list, description="Section content")


# Union type for all content items
ContentItem = Union[
    HeadingContent,
    ParagraphContent,
    ListContent,
    BlockquoteContent,
    SectionContent
]
