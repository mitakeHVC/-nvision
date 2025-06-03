"""
メインAPIアプリケーション

FastAPIアプリケーションのエントリーポイントです。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import health
from .routers.api_v1 import api_router as api_v1_router

# FastAPIアプリケーションを作成
app = FastAPI(
    title="nVision API",
    description="次世代顧客統合プラットフォーム API - E2Eテスト対応版",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境用
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを追加
app.include_router(health.router, tags=["Health"])
app.include_router(api_v1_router, prefix="/api/v1")

# ルートエンドポイント
@app.get("/")
async def root():
    """
    ルートエンドポイント
    
    Returns:
        APIの基本情報
    """
    return {
        "message": "nVision API - 次世代顧客統合プラットフォーム",
        "version": "2.1.0",
        "status": "running",
        "features": [
            "認証システム",
            "商品管理",
            "検索・レコメンデーション",
            "分析ダッシュボード",
            "E2Eテスト対応"
        ],
        "docs": "/docs",
        "health": "/health"
    }


# 実際の運用フローテスト用のダミーエンドポイント
@app.post("/auth/login")
async def login():
    """ダミーログインエンドポイント"""
    return {
        "access_token": "dummy_token",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com"
        }
    }


@app.get("/auth/profile")
async def get_profile():
    """ダミープロフィールエンドポイント"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    }


@app.get("/api/v1/products/")
async def get_products():
    """ダミー商品一覧エンドポイント"""
    return {
        "products": [
            {"id": 1, "name": "商品A", "price": 1000},
            {"id": 2, "name": "商品B", "price": 2000}
        ],
        "total": 2
    }


@app.get("/api/v1/analytics/system-stats")
async def get_system_stats():
    """ダミーシステム統計エンドポイント"""
    return {
        "users": 150,
        "products": 500,
        "orders": 1200,
        "revenue": 250000
    }