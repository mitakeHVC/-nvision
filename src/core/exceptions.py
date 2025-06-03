"""
Core Application Exceptions

Defines base and shared custom exceptions for the application.
These exceptions are intended to be used across different layers (services, repositories).
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status # Kept for reference if any core exceptions *need* to be HTTPExceptions

# Base application exception
class AppException(Exception):
    """Base class for other custom exceptions in the application."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message

# General Service and Repository Layer Exceptions
class ServiceException(AppException):
    """Service layer generic exception."""
    pass

class DatabaseException(AppException):
    """Database operation layer generic exception."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.original_exception = original_exception

class NotFoundException(AppException):
    """Raised when a requested resource is not found."""
    # This can be caught by API layer and converted to HTTP 404
    pass

class AuthenticationError(AppException):
    """Authentication failure exception."""
    # Can be caught by API layer and converted to HTTP 401
    pass

class AuthorizationError(AppException):
    """Authorization failure exception (permission denied)."""
    # Can be caught by API layer and converted to HTTP 403
    pass

class ValidationError(AppException):
    """Data validation failure exception."""
    # Can be caught by API layer and converted to HTTP 422
    pass

class ConflictError(AppException):
    """Resource conflict exception (e.g., item already exists)."""
    # Can be caught by API layer and converted to HTTP 409
    pass

# Note: RateLimitError is very specific to HTTP, so it might stay in api.exceptions
# or be defined here if there's a core rate limiting concept.
# For now, leaving it out of core as it's usually an API gateway or middleware concern.

# Example of how API layer would convert these:
# try:
#     # service call
# except core_exceptions.NotFoundException as e:
#     raise api_exceptions.NotFoundError(str(e)) # Or a specific HTTPException
# except core_exceptions.ValidationError as e:
#     raise api_exceptions.ValidationError(str(e), details=e.details)
