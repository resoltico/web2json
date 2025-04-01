"""
Error classes for web2json.

This module defines the custom exceptions used throughout the package.
"""
from typing import Optional


class Web2JsonError(Exception):
    """Base exception for web2json errors."""
    
    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(message)


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


class ValidationError(Web2JsonError):
    """Exception for validation errors."""
    pass


class Result:
    """Result class for handling operation results and errors.
    
    This class provides a way to return either a successful result or an error
    from a function, similar to Rust's Result type or the Either monad.
    """
    
    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error
    
    @property
    def is_success(self) -> bool:
        """Return True if the result is successful."""
        return self._error is None
    
    @property
    def is_error(self) -> bool:
        """Return True if the result is an error."""
        return self._error is not None
    
    @property
    def value(self):
        """Return the value if successful, or raise the error."""
        if self._error:
            raise self._error
        return self._value
    
    @property
    def error(self) -> Optional[Exception]:
        """Return the error if present, or None."""
        return self._error
    
    @classmethod
    def success(cls, value=None):
        """Create a successful result."""
        return cls(value=value)
    
    @classmethod
    def failure(cls, error):
        """Create a failure result."""
        if not isinstance(error, Exception):
            error = Web2JsonError(str(error))
        return cls(error=error)
    
    def __bool__(self):
        """Return True if the result is successful."""
        return self.is_success
