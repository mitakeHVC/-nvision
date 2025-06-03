"""
製品データリポジトリ

製品データのCRUD操作を提供
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime

from .base import BaseRepository, EntityNotFoundError, DuplicateEntityError
from ..data_models.ec_models import Product

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository[Product]):
    """
    製品データリポジトリ
    
    製品データの永続化とクエリ操作を提供
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        super().__init__()
        # インメモリストレージ（実際の実装ではデータベース接続を使用）
        self._products: Dict[int, Product] = {}
        self._next_id = 1
        
        # サンプルデータの初期化
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """サンプルデータの初期化"""
        sample_products = [
            Product(
                ProductID=1,
                ProductName="ノートパソコン",
                Description="高性能なビジネス向けノートパソコン",
                SKU="NB-001",
                CategoryID=1,
                SupplierID=1,
                Price=120000.0,
                StockQuantity=50,
                ImagePath="/images/notebook1.jpg",
                DateAdded=datetime.now()
            ),
            Product(
                ProductID=2,
                ProductName="ワイヤレスマウス",
                Description="エルゴノミクスデザインのワイヤレスマウス",
                SKU="MS-001",
                CategoryID=2,
                SupplierID=2,
                Price=3500.0,
                StockQuantity=200,
                ImagePath="/images/mouse1.jpg",
                DateAdded=datetime.now()
            ),
            Product(
                ProductID=3,
                ProductName="メカニカルキーボード",
                Description="プログラマー向け高品質メカニカルキーボード",
                SKU="KB-001",
                CategoryID=2,
                SupplierID=1,
                Price=15000.0,
                StockQuantity=75,
                ImagePath="/images/keyboard1.jpg",
                DateAdded=datetime.now()
            )
        ]
        
        for product in sample_products:
            self._products[product.ProductID] = product
            self._next_id = max(self._next_id, product.ProductID + 1)
    
    async def create(self, entity: Product) -> Product:
        """製品を作成"""
        try:
            self._log_operation("create_product", sku=entity.SKU)
            
            # SKUの重複チェック
            if entity.SKU and await self.get_by_sku(entity.SKU):
                raise DuplicateEntityError(f"Product with SKU {entity.SKU} already exists")
            
            # IDが指定されていない場合は自動生成
            if not hasattr(entity, 'ProductID') or entity.ProductID is None:
                entity.ProductID = self._next_id
                self._next_id += 1
            
            # 作成日時の設定
            if not entity.DateAdded:
                entity.DateAdded = datetime.now()
            
            self._products[entity.ProductID] = entity
            
            self.logger.info(f"Product created successfully: {entity.ProductID}")
            return entity
            
        except Exception as e:
            self._handle_error("create_product", e)
    
    async def get_by_id(self, entity_id: UUID) -> Optional[Product]:
        """IDで製品を取得"""
        try:
            # UUIDをintに変換（実際の実装では適切な変換を行う）
            product_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("get_product_by_id", entity_id=entity_id)
            
            product = self._products.get(product_id)
            if product:
                self.logger.info(f"Product found: {product_id}")
            else:
                self.logger.info(f"Product not found: {product_id}")
            
            return product
            
        except Exception as e:
            self._handle_error("get_product_by_id", e, entity_id)
    
    async def get_by_product_id(self, product_id: int) -> Optional[Product]:
        """製品IDで製品を取得"""
        try:
            self._log_operation("get_product_by_product_id", product_id=product_id)
            
            product = self._products.get(product_id)
            if product:
                self.logger.info(f"Product found: {product_id}")
            else:
                self.logger.info(f"Product not found: {product_id}")
            
            return product
            
        except Exception as e:
            self._handle_error("get_product_by_product_id", e)
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """SKUで製品を取得"""
        try:
            self._log_operation("get_product_by_sku", sku=sku)
            
            for product in self._products.values():
                if product.SKU == sku:
                    self.logger.info(f"Product found by SKU: {sku}")
                    return product
            
            self.logger.info(f"Product not found by SKU: {sku}")
            return None
            
        except Exception as e:
            self._handle_error("get_product_by_sku", e)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """全ての製品を取得"""
        try:
            self._log_operation("get_all_products", limit=limit, offset=offset)
            
            products = list(self._products.values())
            products.sort(key=lambda x: x.ProductID)
            
            result = products[offset:offset + limit]
            
            self.logger.info(f"Retrieved {len(result)} products")
            return result
            
        except Exception as e:
            self._handle_error("get_all_products", e)
    
    async def update(self, entity_id: UUID, update_data: Dict[str, Any]) -> Optional[Product]:
        """製品を更新"""
        try:
            # UUIDをintに変換
            product_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("update_product", entity_id=entity_id, update_data=update_data)
            
            product = self._products.get(product_id)
            if not product:
                self.logger.warning(f"Product not found for update: {product_id}")
                return None
            
            # 更新データを適用
            product_dict = product.dict()
            product_dict.update(update_data)
            
            # 更新された製品エンティティを作成
            updated_product = Product(**product_dict)
            self._products[product_id] = updated_product
            
            self.logger.info(f"Product updated successfully: {product_id}")
            return updated_product
            
        except Exception as e:
            self._handle_error("update_product", e, entity_id)
    
    async def delete(self, entity_id: UUID) -> bool:
        """製品を削除"""
        try:
            # UUIDをintに変換
            product_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("delete_product", entity_id=entity_id)
            
            if product_id in self._products:
                del self._products[product_id]
                self.logger.info(f"Product deleted successfully: {product_id}")
                return True
            else:
                self.logger.warning(f"Product not found for deletion: {product_id}")
                return False
                
        except Exception as e:
            self._handle_error("delete_product", e, entity_id)
            return False
    
    async def exists(self, entity_id: UUID) -> bool:
        """製品の存在確認"""
        try:
            # UUIDをintに変換
            product_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("product_exists", entity_id=entity_id)
            
            exists = product_id in self._products
            self.logger.info(f"Product exists check: {product_id} -> {exists}")
            return exists
            
        except Exception as e:
            self._handle_error("product_exists", e, entity_id)
            return False
    
    async def search_by_name(self, name: str) -> List[Product]:
        """名前で製品を検索"""
        try:
            self._log_operation("search_products_by_name", name=name)
            
            results = []
            for product in self._products.values():
                if name.lower() in (product.ProductName or '').lower():
                    results.append(product)
            
            self.logger.info(f"Found {len(results)} products matching name: {name}")
            return results
            
        except Exception as e:
            self._handle_error("search_products_by_name", e)
            return []
    
    async def get_by_category(self, category_id: int) -> List[Product]:
        """カテゴリIDで製品を取得"""
        try:
            self._log_operation("get_products_by_category", category_id=category_id)
            
            results = []
            for product in self._products.values():
                if product.CategoryID == category_id:
                    results.append(product)
            
            self.logger.info(f"Found {len(results)} products in category: {category_id}")
            return results
            
        except Exception as e:
            self._handle_error("get_products_by_category", e)
            return []