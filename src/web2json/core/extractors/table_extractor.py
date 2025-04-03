"""
Table extractor module for web2json.

This module provides functionality for extracting tables from HTML.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from web2json.models.content import TableContent
from web2json.utils.errors import ExtractError
from web2json.core.extractors.base import get_element_text


def extract_tables(soup: BeautifulSoup, preserve_styles: bool = False) -> List[TableContent]:
    """Extract tables from HTML content.
    
    Args:
        soup: BeautifulSoup object to extract tables from
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of TableContent objects
        
    Raises:
        ExtractError: If table extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        tables = []
        
        # Process table elements
        for table in soup.find_all("table"):
            table_content = extract_table(table, preserve_styles)
            if table_content:
                tables.append(table_content)
        
        logger.debug(f"Extracted {len(tables)} tables from document")
        return tables
        
    except Exception as e:
        logger.error(f"Error extracting tables: {str(e)}")
        raise ExtractError(f"Failed to extract tables: {str(e)}")


def extract_table(table: Tag, preserve_styles: bool = False) -> Optional[TableContent]:
    """Extract content from a single table.
    
    Args:
        table: Table tag to extract
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        TableContent object or None if extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Extract caption if present
        caption = None
        caption_tag = table.find("caption")
        if caption_tag:
            caption = get_element_text(caption_tag, preserve_styles)
        
        # Extract headers
        headers = None
        
        # Try to get headers from thead
        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")
            if header_row:
                headers = [
                    get_element_text(th, preserve_styles)
                    for th in header_row.find_all(["th", "td"])
                ]
        
        # If no headers found in thead, try first row
        if not headers:
            first_row = table.find("tr")
            if first_row and first_row.find("th"):
                headers = [
                    get_element_text(th, preserve_styles)
                    for th in first_row.find_all("th")
                ]
        
        # Extract rows
        rows = []
        
        # Get body rows (skip header row if it was used for headers)
        body_rows = table.find_all("tr")
        start_idx = 0
        
        # If the first row was used for headers, skip it
        if headers and body_rows and not thead:
            if body_rows[0].find("th") and not body_rows[0].find("td"):
                start_idx = 1
        
        # Process remaining rows
        for i in range(start_idx, len(body_rows)):
            row = body_rows[i]
            # Get all cells in the row
            cells = [
                get_element_text(cell, preserve_styles)
                for cell in row.find_all(["td", "th"])
            ]
            if cells:  # Only add non-empty rows
                rows.append(cells)
        
        # Skip tables with no data
        if not rows:
            logger.debug("Skipping empty table")
            return None
        
        # Create TableContent
        table_content = {
            "type": "table",
            "caption": caption,
            "headers": headers,
            "rows": rows
        }
        
        return table_content
        
    except Exception as e:
        logger.warning(f"Error extracting table: {str(e)}")
        return None


def detect_table_structure(table: Tag) -> Dict[str, Any]:
    """Detect the structure of a table.
    
    Args:
        table: Table element to analyze
        
    Returns:
        Dictionary with table structure information
    """
    info = {
        "has_headers": False,
        "row_count": 0,
        "column_count": 0,
        "has_caption": False
    }
    
    # Check for caption
    caption = table.find("caption")
    info["has_caption"] = caption is not None
    
    # Count rows
    rows = table.find_all("tr")
    info["row_count"] = len(rows)
    
    # Check for headers
    thead = table.find("thead")
    if thead and thead.find("th"):
        info["has_headers"] = True
    elif rows and rows[0].find("th"):
        info["has_headers"] = True
    
    # Estimate column count from the first row with cells
    for row in rows:
        cells = row.find_all(["td", "th"])
        if cells:
            info["column_count"] = len(cells)
            break
    
    return info


def is_data_table(table: Tag) -> bool:
    """Try to determine if a table is used for data or layout.
    
    Args:
        table: Table element to analyze
        
    Returns:
        True if the table likely contains data, False if it's likely for layout
    """
    # Tables with headers are likely data tables
    if table.find("th") or table.find("thead"):
        return True
    
    # Tables with captions are likely data tables
    if table.find("caption"):
        return True
    
    # Count rows and columns
    rows = table.find_all("tr")
    
    # No rows or only one row is likely a layout table
    if len(rows) <= 1:
        return False
    
    # Count cells in each row
    cell_counts = []
    for row in rows:
        cell_counts.append(len(row.find_all(["td", "th"])))
    
    # If all rows have the same number of cells, it's likely a data table
    if len(set(cell_counts)) == 1 and cell_counts[0] > 1:
        return True
    
    # If the table has a border attribute, it's likely a data table
    if table.has_attr("border") and int(table.get("border", "0")) > 0:
        return True
    
    # Check for structural elements
    if (table.find("tbody") or table.find("tfoot") or
        table.has_attr("summary") or table.has_attr("role") == "grid"):
        return True
    
    # Default to assuming it's a layout table
    return False
