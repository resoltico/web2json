"""
Content models module for web2json.

This module defines the Pydantic models for content items in the document.
"""
from typing import List, Optional, Union, Literal, Dict, Any, ForwardRef

from pydantic import BaseModel, Field


class BaseContentItem(BaseModel):
    """Base class for all content items."""
    
    type: str = Field(..., description="Type of content item")


class HeadingContent(BaseContentItem):
    """Content model for headings."""
    
    type: Literal["heading"] = Field("heading", description="Type of content item")
    level: int = Field(1, description="Heading level (1-6)", ge=1, le=6)
    text: str = Field("", description="Heading text")
    id: Optional[str] = Field(None, description="Optional ID for anchoring")


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


class CodeContent(BaseContentItem):
    """Content model for code blocks."""
    
    type: Literal["code_block"] = Field("code_block", description="Type of content item")
    text: str = Field("", description="Code content")
    language: Optional[str] = Field(None, description="Programming language")
    caption: Optional[str] = Field(None, description="Code block caption or title")


class ImageContent(BaseContentItem):
    """Content model for images."""
    
    type: Literal["image"] = Field("image", description="Type of content item")
    src: str = Field(..., description="Image source URL")
    alt: Optional[str] = Field(None, description="Alternative text")
    caption: Optional[str] = Field(None, description="Image caption")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")


class TableContent(BaseContentItem):
    """Content model for tables."""
    
    type: Literal["table"] = Field("table", description="Type of content item")
    caption: Optional[str] = Field(None, description="Table caption")
    headers: Optional[List[str]] = Field(None, description="Table header cells")
    rows: List[List[str]] = Field(default_factory=list, description="Table rows")


# Use ForwardRef to handle recursive SectionContent
SectionContentRef = ForwardRef("SectionContent")

class SectionContent(BaseContentItem):
    """Content model for document sections."""
    
    type: Literal["section"] = Field("section", description="Type of content item")
    level: int = Field(1, description="Section level")
    content: List[Union[
        HeadingContent, 
        ParagraphContent, 
        ListContent, 
        BlockquoteContent,
        CodeContent,
        ImageContent,
        TableContent,
        SectionContentRef
    ]] = Field(default_factory=list, description="Section content")


# Update the model to support recursive definitions
SectionContent.model_rebuild()


# Union type for all content items
ContentItem = Union[
    HeadingContent,
    ParagraphContent,
    ListContent,
    BlockquoteContent,
    CodeContent,
    ImageContent,
    TableContent,
    SectionContent
]
