"""
API v1 ルーターモジュール

バージョン1のAPIエンドポイントを提供します。
"""

from fastapi import APIRouter

from .endpoints import customers, products, search, analytics, client_preferences, suggestions, reports

# API v1 ルーター
api_router = APIRouter()

# エンドポイントを含める
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(client_preferences.router, prefix="/client-preferences", tags=["client-preferences"])
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

__all__ = ["api_router"]