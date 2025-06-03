"""
リポジトリパッケージ

データアクセス層のリポジトリパターン実装
"""

from .base import BaseRepository
from .customer_repository import CustomerRepository
from .product_repository import ProductRepository
from .order_repository import OrderRepository
from .crm_repository import CRMRepository
from .vector_repository import VectorRepository

__all__ = [
    "BaseRepository",
    "CustomerRepository", 
    "ProductRepository",
    "OrderRepository",
    "CRMRepository",
    "VectorRepository"
]