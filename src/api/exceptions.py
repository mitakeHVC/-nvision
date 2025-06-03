"""
API例外ハンドラー

カスタム例外とエラーハンドリングを提供します。
"""

import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

from ..config.auth_config import get_auth_settings

logger = logging.getLogger(__name__)
auth_settings = get_auth_settings()


# === カスタム例外クラス ===

class APIException(Exception):
    """API基本例外クラス"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIException):
    """認証エラー"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(APIException):
    """認可エラー"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class ValidationError(APIException):
    """バリデーションエラー"""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class NotFoundError(APIException):
    """リソース未発見エラー"""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND_ERROR",
            details=details
        )


class ConflictError(APIException):
    """競合エラー"""
    
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
            details=details
        )


class RateLimitError(APIException):
    """レート制限エラー"""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            details=details
        )


class ServiceUnavailableError(APIException):
    """サービス利用不可エラー"""
    
    def __init__(self, message: str = "Service temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE_ERROR",
            details=details
        )


class DatabaseError(APIException):
    """データベースエラー"""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details
        )


class ExternalServiceError(APIException):
    """外部サービスエラー"""
    
    def __init__(self, message: str = "External service error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


# === エラーレスポンス生成 ===

def create_error_response(
    message: str,
    status_code: int,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """エラーレスポンスを生成"""
    
    error_response = {
        "error": {
            "message": message,
            "code": error_code,
            "status_code": status_code
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    if request_id:
        error_response["request_id"] = request_id
    
    # デバッグモードでは追加情報を含める
    if auth_settings.debug_mode:
        error_response["debug"] = {
            "timestamp": str(logger.handlers[0].formatter.formatTime(logger.makeRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            )) if logger.handlers else ""),
            "environment": "development"
        }
    
    return error_response


# === 例外ハンドラー ===

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """API例外ハンドラー"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # ログ記録
    logger.error(
        f"API Exception: {exc.error_code or 'UNKNOWN'} - {exc.message} "
        f"(Request ID: {request_id})"
    )
    
    if auth_settings.debug_mode:
        logger.debug(f"Exception details: {exc.details}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            message=exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            details=exc.details,
            request_id=request_id
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP例外ハンドラー"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # ログ記録
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} "
        f"(Request ID: {request_id})"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            message=str(exc.detail),
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            request_id=request_id
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """バリデーション例外ハンドラー"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # バリデーションエラーの詳細を整理
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    # ログ記録
    logger.warning(
        f"Validation Error: {len(validation_errors)} errors "
        f"(Request ID: {request_id})"
    )
    
    if auth_settings.debug_mode:
        logger.debug(f"Validation errors: {validation_errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            message="Validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"validation_errors": validation_errors},
            request_id=request_id
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """一般例外ハンドラー"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # ログ記録
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)} "
        f"(Request ID: {request_id})"
    )
    
    if auth_settings.debug_mode:
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # 本番環境では詳細なエラー情報を隠す
    if auth_settings.debug_mode:
        message = f"{type(exc).__name__}: {str(exc)}"
        details = {"traceback": traceback.format_exc().split("\n")}
    else:
        message = "Internal server error"
        details = None
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            details=details,
            request_id=request_id
        )
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Starlette HTTP例外ハンドラー"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # ログ記録
    logger.warning(
        f"Starlette HTTP Exception: {exc.status_code} - {exc.detail} "
        f"(Request ID: {request_id})"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            message=str(exc.detail),
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            request_id=request_id
        )
    )


# === 例外ハンドラー設定 ===

def setup_exception_handlers(app: FastAPI) -> None:
    """例外ハンドラーを設定"""
    
    # カスタム例外
    app.add_exception_handler(APIException, api_exception_handler)
    
    # FastAPI例外
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Starlette例外
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    
    # 一般例外
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers configured")


# === 例外発生ヘルパー ===

def raise_authentication_error(message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
    """認証エラーを発生"""
    raise AuthenticationError(message, details)


def raise_authorization_error(message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
    """認可エラーを発生"""
    raise AuthorizationError(message, details)


def raise_validation_error(message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
    """バリデーションエラーを発生"""
    raise ValidationError(message, details)


def raise_not_found_error(resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
    """リソース未発見エラーを発生"""
    raise NotFoundError(f"{resource} not found", details)


def raise_conflict_error(message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
    """競合エラーを発生"""
    raise ConflictError(message, details)


def raise_rate_limit_error(message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
    """レート制限エラーを発生"""
    raise RateLimitError(message, details)


def raise_service_unavailable_error(message: str = "Service temporarily unavailable", details: Optional[Dict[str, Any]] = None):
    """サービス利用不可エラーを発生"""
    raise ServiceUnavailableError(message, details)


def raise_database_error(message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
    """データベースエラーを発生"""
    raise DatabaseError(message, details)


def raise_external_service_error(service: str = "External service", details: Optional[Dict[str, Any]] = None):
    """外部サービスエラーを発生"""
    raise ExternalServiceError(f"{service} error", details)


# === エラー処理デコレータ ===

def handle_exceptions(
    default_message: str = "Operation failed",
    log_errors: bool = True
):
    """例外処理デコレータ"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except APIException:
                # API例外はそのまま再発生
                raise
            except Exception as e:
                if log_errors:
                    logger.error(f"Exception in {func.__name__}: {str(e)}")
                    if auth_settings.debug_mode:
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
                # 一般例外をAPI例外に変換
                raise APIException(
                    message=default_message,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_code="OPERATION_FAILED",
                    details={"original_error": str(e)} if auth_settings.debug_mode else None
                )
        
        return wrapper
    return decorator