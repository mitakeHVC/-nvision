"""
FastAPI メインアプリケーション

認証・認可システムを含むAPIアプリケーションのエントリーポイントです。
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from .routers import auth, health
from .routers.api_v1 import api_router
from .middleware import SecurityMiddleware, RateLimitMiddleware, LoggingMiddleware
from .exceptions import setup_exception_handlers
from ..config.auth_config import get_auth_settings, get_security_settings
from ..auth.security import SecurityManager

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定取得
auth_settings = get_auth_settings()
security_settings = get_security_settings()

# FastAPIアプリケーション作成
app = FastAPI(
    title="nvision API",
    description="統合データ分析・検索プラットフォーム API",
    version="1.0.0",
    docs_url="/docs" if auth_settings.debug_mode else None,
    redoc_url="/redoc" if auth_settings.debug_mode else None,
    openapi_url="/openapi.json" if auth_settings.debug_mode else None
)

# セキュリティマネージャー
security_manager = SecurityManager()


# === ミドルウェア設定 ===

# セキュリティヘッダーミドルウェア
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """セキュリティヘッダーを追加"""
    response = await call_next(request)
    
    if security_settings.security_headers_enabled:
        headers = security_manager.get_security_headers()
        for name, value in headers.items():
            response.headers[name] = value
    
    return response


# パフォーマンス測定ミドルウェア
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """処理時間ヘッダーを追加"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# CORS設定
if auth_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=auth_settings.cors_origins,
        allow_credentials=auth_settings.cors_allow_credentials,
        allow_methods=auth_settings.cors_allow_methods,
        allow_headers=auth_settings.cors_allow_headers,
    )

# 信頼できるホスト設定
if not auth_settings.debug_mode:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.nvision.com"]
    )

# カスタムミドルウェア
app.add_middleware(SecurityMiddleware, security_manager=security_manager)
app.add_middleware(RateLimitMiddleware, security_manager=security_manager)
app.add_middleware(LoggingMiddleware)


# === イベントハンドラー ===

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("nvision API starting up...")
    
    # データベース接続初期化
    # await init_database()
    
    # キャッシュ初期化
    # await init_cache()
    
    logger.info("nvision API startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("nvision API shutting down...")
    
    # データベース接続クリーンアップ
    # await cleanup_database()
    
    # キャッシュクリーンアップ
    # await cleanup_cache()
    
    logger.info("nvision API shutdown completed")


# === ルーター設定 ===

# ヘルスチェック
app.include_router(health.router, prefix="/health", tags=["health"])

# 認証エンドポイント
app.include_router(auth.router, prefix="/auth", tags=["authentication"])

# API v1
app.include_router(api_router, prefix="/api/v1")


# === 例外ハンドラー設定 ===
setup_exception_handlers(app)


# === ルートエンドポイント ===

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "nvision API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs" if auth_settings.debug_mode else None
    }


@app.get("/info")
async def info():
    """API情報エンドポイント"""
    return {
        "name": "nvision API",
        "version": "1.0.0",
        "description": "統合データ分析・検索プラットフォーム API",
        "features": [
            "JWT認証",
            "ロールベースアクセス制御",
            "レート制限",
            "セキュリティヘッダー",
            "監査ログ",
            "ベクトル検索",
            "セマンティック検索",
            "レコメンデーション",
            "分析機能"
        ],
        "endpoints": {
            "health": "/health",
            "auth": "/auth",
            "api": "/api/v1",
            "docs": "/docs" if auth_settings.debug_mode else None
        }
    }


@app.get("/security/stats")
async def security_stats():
    """セキュリティ統計エンドポイント（デバッグ用）"""
    if not auth_settings.debug_mode:
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    
    return security_manager.get_security_stats()


# === エラーハンドリング ===

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404エラーハンドラー"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500エラーハンドラー"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=auth_settings.debug_mode,
        log_level="info"
    )