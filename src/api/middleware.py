"""
APIミドルウェア

セキュリティ、レート制限、ログ記録などのミドルウェアを提供します。
"""

import time
import json
import logging
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..auth.security import SecurityManager
from ..config.auth_config import get_auth_settings, get_security_settings

logger = logging.getLogger(__name__)

# 設定取得
auth_settings = get_auth_settings()
security_settings = get_security_settings()


class SecurityMiddleware(BaseHTTPMiddleware):
    """セキュリティミドルウェア"""
    
    def __init__(self, app: ASGIApp, security_manager: SecurityManager):
        super().__init__(app)
        self.security_manager = security_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """セキュリティチェックを実行"""
        try:
            # クライアント情報取得
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            # セキュリティイベントログ
            if security_settings.log_security_events:
                logger.info(f"Request from {client_ip}: {request.method} {request.url.path}")
            
            # セッション検証（必要に応じて）
            if hasattr(request.state, "session_token"):
                session_valid = self.security_manager.validate_session(
                    request.state.session_token,
                    client_ip,
                    user_agent
                )
                if not session_valid:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid session"}
                    )
            
            # リクエスト処理
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Security check failed"}
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """レート制限ミドルウェア"""
    
    def __init__(self, app: ASGIApp, security_manager: SecurityManager):
        super().__init__(app)
        self.security_manager = security_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """レート制限をチェック"""
        try:
            # レート制限が無効な場合はスキップ
            if not auth_settings.rate_limit_enabled or auth_settings.disable_rate_limiting:
                return await call_next(request)
            
            # クライアント情報取得
            client_ip = request.client.host if request.client else "unknown"
            
            # エンドポイント判定
            endpoint = self._get_endpoint_type(request.url.path)
            
            # ユーザーID取得（認証済みの場合）
            user_id = getattr(request.state, "user_id", None)
            
            # レート制限チェック
            allowed, error_message = self.security_manager.check_rate_limit(
                client_ip=client_ip,
                endpoint=endpoint,
                user_id=user_id
            )
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": error_message or "Rate limit exceeded",
                        "retry_after": 60  # 1分後に再試行
                    },
                    headers={"Retry-After": "60"}
                )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            return await call_next(request)
    
    def _get_endpoint_type(self, path: str) -> str:
        """パスからエンドポイントタイプを判定"""
        if path.startswith("/auth/login"):
            return "login"
        elif path.startswith("/auth/"):
            return "auth"
        elif path.startswith("/api/v1/search"):
            return "search"
        elif path.startswith("/auth/password-reset"):
            return "password_reset"
        else:
            return "api"


class LoggingMiddleware(BaseHTTPMiddleware):
    """ログ記録ミドルウェア"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """リクエスト・レスポンスをログ記録"""
        start_time = time.time()
        
        # リクエスト情報
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        method = request.method
        url = str(request.url)
        
        # リクエストログ
        logger.info(f"Request: {method} {url} from {client_ip}")
        
        try:
            # リクエスト処理
            response = await call_next(request)
            
            # 処理時間計算
            process_time = time.time() - start_time
            
            # レスポンスログ
            logger.info(
                f"Response: {response.status_code} for {method} {url} "
                f"({process_time:.3f}s)"
            )
            
            # 詳細ログ（デバッグモード時）
            if auth_settings.debug_mode:
                logger.debug(
                    f"Request details: IP={client_ip}, "
                    f"User-Agent={user_agent}, "
                    f"Process-Time={process_time:.3f}s"
                )
            
            return response
            
        except Exception as e:
            # エラーログ
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {method} {url} from {client_ip} "
                f"({process_time:.3f}s) - {str(e)}"
            )
            raise


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF保護ミドルウェア"""
    
    def __init__(self, app: ASGIApp, security_manager: SecurityManager):
        super().__init__(app)
        self.security_manager = security_manager
        self.exempt_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",  # ログインは除外
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """CSRF保護をチェック"""
        try:
            # CSRF保護が無効な場合はスキップ
            if not security_settings.enable_csrf_protection:
                return await call_next(request)
            
            # 除外パスの場合はスキップ
            if any(request.url.path.startswith(path) for path in self.exempt_paths):
                return await call_next(request)
            
            # 安全なメソッドの場合はスキップ
            if request.method in ["GET", "HEAD", "OPTIONS"]:
                return await call_next(request)
            
            # CSRFトークンチェック
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF token required"}
                )
            
            # セッショントークン取得（実際の実装では適切に取得）
            session_token = getattr(request.state, "session_token", "")
            
            # CSRFトークン検証
            if not self.security_manager.validate_csrf_token(csrf_token, session_token):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Invalid CSRF token"}
                )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"CSRF middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "CSRF check failed"}
            )


class CompressionMiddleware(BaseHTTPMiddleware):
    """レスポンス圧縮ミドルウェア"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """レスポンスを圧縮"""
        response = await call_next(request)
        
        # 圧縮対象のコンテンツタイプ
        compressible_types = [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript"
        ]
        
        # Accept-Encodingヘッダーチェック
        accept_encoding = request.headers.get("accept-encoding", "")
        content_type = response.headers.get("content-type", "")
        
        # 圧縮条件チェック
        if ("gzip" in accept_encoding and 
            any(ct in content_type for ct in compressible_types) and
            response.status_code == 200):
            
            # 実際の圧縮実装はここに追加
            # response.headers["Content-Encoding"] = "gzip"
            pass
        
        return response


class CacheMiddleware(BaseHTTPMiddleware):
    """キャッシュミドルウェア"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.cache = {}  # 実際の実装ではRedisなどを使用
        self.cacheable_paths = [
            "/api/v1/products",
            "/api/v1/customers",
            "/health"
        ]
        self.cache_ttl = 300  # 5分
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """キャッシュをチェック"""
        # GETリクエストのみキャッシュ
        if request.method != "GET":
            return await call_next(request)
        
        # キャッシュ対象パスかチェック
        if not any(request.url.path.startswith(path) for path in self.cacheable_paths):
            return await call_next(request)
        
        # キャッシュキー生成
        cache_key = f"{request.method}:{request.url.path}:{request.url.query}"
        
        # キャッシュヒットチェック
        if cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]
            if (time.time() - timestamp) < self.cache_ttl:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_response
            else:
                del self.cache[cache_key]
        
        # レスポンス取得
        response = await call_next(request)
        
        # 成功レスポンスをキャッシュ
        if response.status_code == 200:
            self.cache[cache_key] = (response, time.time())
            logger.debug(f"Cache miss: {cache_key}")
        
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """リクエストID追加ミドルウェア"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """リクエストIDを追加"""
        import uuid
        
        # リクエストID生成
        request_id = str(uuid.uuid4())
        
        # リクエストステートに保存
        request.state.request_id = request_id
        
        # レスポンス処理
        response = await call_next(request)
        
        # レスポンスヘッダーに追加
        response.headers["X-Request-ID"] = request_id
        
        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """ヘルスチェックミドルウェア"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """ヘルスチェック処理"""
        # ヘルスチェックパスの場合は高速処理
        if request.url.path == "/health":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": time.time(),
                    "version": "1.0.0"
                }
            )
        
        return await call_next(request)