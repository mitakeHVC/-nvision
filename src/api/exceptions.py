"""
API例外処理

カスタム例外クラスと例外ハンドラーを定義します。
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from functools import wraps


class AuthenticationError(HTTPException):
    """認証エラー"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": message, "details": details or {}}
        )


class AuthorizationError(HTTPException):
    """認可エラー"""
    def __init__(self, message: str = "Authorization failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": message, "details": details or {}}
        )


class ValidationError(HTTPException):
    """バリデーションエラー"""
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": message, "details": details or {}}
        )


class NotFoundError(HTTPException):
    """リソースが見つからないエラー"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": message, "details": details or {}}
        )


class ConflictError(HTTPException):
    """競合エラー"""
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": message, "details": details or {}}
        )


class RateLimitError(HTTPException):
    """レート制限エラー"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": message, "details": details or {}}
        )


def handle_exceptions(operation_name: str):
    """例外処理デコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # HTTPExceptionはそのまま再発生
                raise
            except Exception as e:
                # その他の例外は内部サーバーエラーとして処理
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "message": f"{operation_name} failed due to internal error",
                        "details": {"error": str(e)}
                    }
                )
        return wrapper
    return decorator