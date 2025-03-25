"""
Custom exceptions for web2json.
"""

class Web2JsonError(Exception):
    """Base exception for web2json errors."""
    pass


class PathError(Web2JsonError):
    """Exception for path-related errors."""
    pass


class FetchError(Web2JsonError):
    """Exception for URL fetching errors."""
    pass


class ParseError(Web2JsonError):
    """Exception for HTML parsing errors."""
    pass


class ExtractError(Web2JsonError):
    """Exception for content extraction errors."""
    pass


class TransformError(Web2JsonError):
    """Exception for content transformation errors."""
    pass


class ExportError(Web2JsonError):
    """Exception for document export errors."""
    pass


class ConversionError(Web2JsonError):
    """Exception for JSON conversion errors."""
    pass
