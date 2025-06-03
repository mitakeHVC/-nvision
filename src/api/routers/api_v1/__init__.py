"""
API v1 ルーターモジュール

バージョン1のAPIエンドポイントを提供します。
"""

from fastapi import APIRouter

from .endpoints import customers, products, search

# API v1 ルーター
api_router = APIRouter()

# エンドポイントを含める
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(search.router, prefix="/search", tags=["search"])

__all__ = ["api_router"]