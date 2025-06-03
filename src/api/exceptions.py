"""
API例外処理

カスタムHTTP関連例外クラスと例外ハンドラーを定義します。
汎用アプリケーション例外は src.core.exceptions を参照してください。
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from functools import wraps
from src.core.exceptions import ( # Importing core exceptions to be potentially wrapped
    NotFoundException as CoreNotFoundException,
    AuthenticationError as CoreAuthenticationError,
    AuthorizationError as CoreAuthorizationError,
    ValidationError as CoreValidationError,
    ConflictError as CoreConflictError,
    ServiceException as CoreServiceException,
    DatabaseException as CoreDatabaseException,
    AppException as CoreAppException, # Base app exception
)

# HTTP Specific Exceptions - these can wrap core exceptions or be used directly by API layer

class APIAuthenticationError(HTTPException):
    """HTTP 401 Authentication Error"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": message, "details": details or {}}
        )

class APIAuthorizationError(HTTPException):
    """HTTP 403 Authorization Error"""
    def __init__(self, message: str = "Authorization failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": message, "details": details or {}}
        )

class APIValidationError(HTTPException):
    """HTTP 422 Validation Error"""
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": message, "details": details or {}}
        )

class APINotFoundError(HTTPException):
    """HTTP 404 Not Found Error"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": message, "details": details or {}}
        )

class APIConflictError(HTTPException):
    """HTTP 409 Conflict Error"""
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": message, "details": details or {}}
        )

class APIRateLimitError(HTTPException): # Renamed for consistency, was RateLimitError
    """HTTP 429 Rate Limit Error"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": message, "details": details or {}}
        )

def handle_api_exceptions(operation_name: str): # Renamed for clarity
    """
    API-level exception handling decorator.
    Catches core exceptions and converts them to appropriate API_xxxxError HTTPExceptions.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException: # Let FastAPI handle its own or re-raised HTTPExceptions
                raise
            except CoreNotFoundException as e:
                raise APINotFoundError(message=str(e), details=getattr(e, 'details', None))
            except CoreAuthenticationError as e:
                raise APIAuthenticationError(message=str(e), details=getattr(e, 'details', None))
            except CoreAuthorizationError as e:
                raise APIAuthorizationError(message=str(e), details=getattr(e, 'details', None))
            except CoreValidationError as e:
                raise APIValidationError(message=str(e), details=getattr(e, 'details', None))
            except CoreConflictError as e:
                raise APIConflictError(message=str(e), details=getattr(e, 'details', None))
            except CoreServiceException as e: # Catch-all for other service errors
                # Log the original error e for debugging
                print(f"ServiceException caught in API: {e}") # Replace with proper logging
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"message": f"{operation_name} failed due to a service error: {str(e)}", "details": e.details}
                )
            except CoreDatabaseException as e: # Catch-all for other database errors
                 # Log the original error e for debugging
                print(f"DatabaseException caught in API: {e}") # Replace with proper logging
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"message": f"{operation_name} failed due to a database error: {str(e)}", "details": e.details}
                )
            except CoreAppException as e: # Catch-all for other core app errors
                 # Log the original error e for debugging
                print(f"AppException caught in API: {e}") # Replace with proper logging
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"message": f"{operation_name} failed: {str(e)}", "details": e.details}
                )
            except Exception as e:
                # Log the original error e for debugging
                print(f"Unhandled exception caught in API: {type(e).__name__} - {e}") # Replace with proper logging
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "message": f"{operation_name} failed due to an unexpected internal error."
                        # "details": {"error_type": type(e).__name__, "error_message": str(e)} # Avoid leaking too much detail
                    }
                )
        return wrapper
    return decorator

# Ensure old names are not available for direct import if they were changed.
# The goal is that other modules will now import these from src.core.exceptions.
# This file should only export HTTP-specific exceptions and handlers.
__all__ = [
    "APIAuthenticationError",
    "APIAuthorizationError",
    "APIValidationError",
    "APINotFoundError",
    "APIConflictError",
    "APIRateLimitError",
    "handle_api_exceptions",
]
