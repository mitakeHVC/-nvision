"""
製品ビジネスロジックサービス

製品に関するビジネスロジックを提供
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..repositories.product_repository import ProductRepository
from ..repositories.vector_repository import VectorRepository
from ..data_models.ec_models import Product

logger = logging.getLogger(__name__)


class ProductService:
    """
    製品ビジネスロジックサービス
    
    製品データの操作とビジネスルールの実装
    """
    
    def __init__(self):
        """サービスの初期化"""
        self.product_repository = ProductRepository()
        self.vector_repository = VectorRepository()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def create_product(self, product_data: Dict[str, Any]) -> Product:
        """
        新しい製品を作成
        
        Args:
            product_data: 製品データ
            
        Returns:
            作成された製品エンティティ
            
        Raises:
            ValueError: 無効なデータの場合
            DuplicateEntityError: 重複する製品の場合
        """
        try:
            self.logger.info(f"Creating new product: {product_data.get('ProductName')}")
            
            # データ検証
            self._validate_product_data(product_data)
            
            # 製品エンティティを作成
            product = Product(**product_data)
            
            # リポジトリに保存
            created_product = await self.product_repository.create(product)
            
            # ベクトル検索用のドキュメントを作成
            await self._add_product_to_vector_search(created_product)
            
            self.logger.info(f"Product created successfully: {created_product.ProductID}")
            return created_product
            
        except Exception as e:
            self.logger.error(f"Failed to create product: {e}")
            raise
    
    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """
        IDで製品を取得
        
        Args:
            product_id: 製品ID
            
        Returns:
            製品エンティティまたはNone
        """
        try:
            self.logger.info(f"Getting product by ID: {product_id}")
            
            product = await self.product_repository.get_by_product_id(product_id)
            
            if product:
                self.logger.info(f"Product found: {product_id}")
            else:
                self.logger.info(f"Product not found: {product_id}")
            
            return product
            
        except Exception as e:
            self.logger.error(f"Failed to get product by ID {product_id}: {e}")
            raise
    
    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """
        SKUで製品を取得
        
        Args:
            sku: SKU
            
        Returns:
            製品エンティティまたはNone
        """
        try:
            self.logger.info(f"Getting product by SKU: {sku}")
            
            product = await self.product_repository.get_by_sku(sku)
            
            if product:
                self.logger.info(f"Product found by SKU: {sku}")
            else:
                self.logger.info(f"Product not found by SKU: {sku}")
            
            return product
            
        except Exception as e:
            self.logger.error(f"Failed to get product by SKU {sku}: {e}")
            raise
    
    async def get_all_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """
        全ての製品を取得
        
        Args:
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            製品エンティティのリスト
        """
        try:
            self.logger.info(f"Getting all products: limit={limit}, offset={offset}")
            
            products = await self.product_repository.get_all(limit=limit, offset=offset)
            
            self.logger.info(f"Retrieved {len(products)} products")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to get all products: {e}")
            raise
    
    async def update_product(self, product_id: int, update_data: Dict[str, Any]) -> Optional[Product]:
        """
        製品情報を更新
        
        Args:
            product_id: 製品ID
            update_data: 更新データ
            
        Returns:
            更新された製品エンティティまたはNone
        """
        try:
            self.logger.info(f"Updating product: {product_id}")
            
            # 既存の製品を確認
            existing_product = await self.product_repository.get_by_product_id(product_id)
            if not existing_product:
                self.logger.warning(f"Product not found for update: {product_id}")
                return None
            
            # データ検証
            self._validate_update_data(update_data)
            
            # UUIDを生成（リポジトリのメソッドに合わせる）
            from uuid import uuid4
            entity_id = uuid4()
            
            # 更新実行
            updated_product = await self.product_repository.update(entity_id, update_data)
            
            if updated_product:
                # ベクトル検索のドキュメントも更新
                await self._update_product_in_vector_search(updated_product)
                self.logger.info(f"Product updated successfully: {product_id}")
            
            return updated_product
            
        except Exception as e:
            self.logger.error(f"Failed to update product {product_id}: {e}")
            raise
    
    async def delete_product(self, product_id: int) -> bool:
        """
        製品を削除
        
        Args:
            product_id: 製品ID
            
        Returns:
            削除成功の場合True
        """
        try:
            self.logger.info(f"Deleting product: {product_id}")
            
            # 既存の製品を確認
            existing_product = await self.product_repository.get_by_product_id(product_id)
            if not existing_product:
                self.logger.warning(f"Product not found for deletion: {product_id}")
                return False
            
            # UUIDを生成（リポジトリのメソッドに合わせる）
            from uuid import uuid4
            entity_id = uuid4()
            
            # 削除実行
            success = await self.product_repository.delete(entity_id)
            
            if success:
                # ベクトル検索からも削除
                await self._remove_product_from_vector_search(product_id)
                self.logger.info(f"Product deleted successfully: {product_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete product {product_id}: {e}")
            raise
    
    async def search_products_by_name(self, name: str) -> List[Product]:
        """
        名前で製品を検索
        
        Args:
            name: 検索する名前
            
        Returns:
            マッチした製品エンティティのリスト
        """
        try:
            self.logger.info(f"Searching products by name: {name}")
            
            products = await self.product_repository.search_by_name(name)
            
            self.logger.info(f"Found {len(products)} products matching name: {name}")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to search products by name {name}: {e}")
            raise
    
    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """
        カテゴリIDで製品を取得
        
        Args:
            category_id: カテゴリID
            
        Returns:
            カテゴリに属する製品エンティティのリスト
        """
        try:
            self.logger.info(f"Getting products by category: {category_id}")
            
            products = await self.product_repository.get_by_category(category_id)
            
            self.logger.info(f"Found {len(products)} products in category: {category_id}")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to get products by category {category_id}: {e}")
            raise
    
    async def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """
        在庫が少ない製品を取得
        
        Args:
            threshold: 在庫の閾値
            
        Returns:
            在庫が閾値以下の製品エンティティのリスト
        """
        try:
            self.logger.info(f"Getting low stock products: threshold={threshold}")
            
            products = await self.product_repository.get_low_stock_products(threshold=threshold)
            
            self.logger.info(f"Found {len(products)} low stock products")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to get low stock products: {e}")
            raise
    
    async def get_products_by_price_range(self, min_price: float, max_price: float) -> List[Product]:
        """
        価格範囲で製品を取得
        
        Args:
            min_price: 最低価格
            max_price: 最高価格
            
        Returns:
            価格範囲内の製品エンティティのリスト
        """
        try:
            self.logger.info(f"Getting products by price range: {min_price}-{max_price}")
            
            products = await self.product_repository.get_by_price_range(min_price, max_price)
            
            self.logger.info(f"Found {len(products)} products in price range")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to get products by price range: {e}")
            raise
    
    async def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """
        在庫数を更新
        
        Args:
            product_id: 製品ID
            quantity_change: 在庫変更数（正数で増加、負数で減少）
            
        Returns:
            更新された製品エンティティまたはNone
        """
        try:
            self.logger.info(f"Updating stock for product {product_id}: {quantity_change}")
            
            updated_product = await self.product_repository.update_stock(product_id, quantity_change)
            
            if updated_product:
                self.logger.info(f"Stock updated successfully for product: {product_id}")
                
                # 在庫が少なくなった場合は警告
                if updated_product.StockQuantity is not None and updated_product.StockQuantity <= 5:
                    self.logger.warning(f"Low stock alert for product {product_id}: {updated_product.StockQuantity}")
            
            return updated_product
            
        except Exception as e:
            self.logger.error(f"Failed to update stock for product {product_id}: {e}")
            raise
    
    async def search_products_by_vector(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ベクトル検索で製品を検索
        
        Args:
            query: 検索クエリ
            limit: 取得件数制限
            
        Returns:
            検索結果のリスト
        """
        try:
            self.logger.info(f"Vector search for products: {query}")
            
            # ベクトル検索を実行
            search_results = await self.vector_repository.search_similar(
                collection_type="products",
                query_text=query,
                n_results=limit
            )
            
            # 結果を整形
            results = []
            for result in search_results:
                product_id = result.metadata.get("product_id")
                if product_id:
                    # 製品の詳細情報を取得
                    product = await self.get_product_by_id(product_id)
                    if product:
                        results.append({
                            "product": product,
                            "similarity": result.similarity,
                            "matched_text": result.document
                        })
            
            self.logger.info(f"Found {len(results)} products by vector search")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search products by vector: {e}")
            raise
    
    async def get_product_statistics(self) -> Dict[str, Any]:
        """
        製品統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        try:
            self.logger.info("Getting product statistics")
            
            # 全製品を取得
            all_products = await self.product_repository.get_all()
            
            # 統計計算
            total_products = len(all_products)
            total_stock = sum(p.StockQuantity or 0 for p in all_products)
            total_value = sum((p.Price or 0) * (p.StockQuantity or 0) for p in all_products)
            
            # 在庫切れ製品
            out_of_stock = len([p for p in all_products if (p.StockQuantity or 0) == 0])
            
            # 低在庫製品
            low_stock = len([p for p in all_products if 0 < (p.StockQuantity or 0) <= 10])
            
            # 平均価格
            avg_price = sum(p.Price or 0 for p in all_products) / total_products if total_products > 0 else 0
            
            stats = {
                "total_products": total_products,
                "total_stock": total_stock,
                "total_inventory_value": total_value,
                "out_of_stock_products": out_of_stock,
                "low_stock_products": low_stock,
                "average_price": avg_price,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Product statistics generated: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get product statistics: {e}")
            raise
    
    def _validate_product_data(self, product_data: Dict[str, Any]) -> None:
        """
        製品データの検証
        
        Args:
            product_data: 検証する製品データ
            
        Raises:
            ValueError: 無効なデータの場合
        """
        required_fields = ['ProductName', 'SKU']
        
        for field in required_fields:
            if not product_data.get(field):
                raise ValueError(f"Required field missing: {field}")
        
        # 価格の検証
        price = product_data.get('Price')
        if price is not None and price < 0:
            raise ValueError("Price cannot be negative")
        
        # 在庫数の検証
        stock = product_data.get('StockQuantity')
        if stock is not None and stock < 0:
            raise ValueError("Stock quantity cannot be negative")
    
    def _validate_update_data(self, update_data: Dict[str, Any]) -> None:
        """
        更新データの検証
        
        Args:
            update_data: 検証する更新データ
            
        Raises:
            ValueError: 無効なデータの場合
        """
        # 価格の検証
        price = update_data.get('Price')
        if price is not None and price < 0:
            raise ValueError("Price cannot be negative")
        
        # 在庫数の検証
        stock = update_data.get('StockQuantity')
        if stock is not None and stock < 0:
            raise ValueError("Stock quantity cannot be negative")
    
    async def _add_product_to_vector_search(self, product: Product) -> None:
        """
        製品をベクトル検索に追加
        
        Args:
            product: 製品エンティティ
        """
        try:
            # 製品情報をテキスト化
            product_text = f"{product.ProductName} {product.Description or ''}"
            if product.SKU:
                product_text += f" {product.SKU}"
            
            # メタデータを作成
            metadata = {
                "type": "product",
                "product_id": product.ProductID,
                "sku": product.SKU,
                "category_id": product.CategoryID,
                "price": product.Price,
                "stock_quantity": product.StockQuantity
            }
            
            # ベクトル検索に追加
            await self.vector_repository.add_document(
                collection_type="products",
                document=product_text,
                metadata=metadata,
                document_id=f"product_{product.ProductID}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to add product to vector search: {e}")
    
    async def _update_product_in_vector_search(self, product: Product) -> None:
        """
        ベクトル検索の製品情報を更新
        
        Args:
            product: 製品エンティティ
        """
        try:
            # 製品情報をテキスト化
            product_text = f"{product.ProductName} {product.Description or ''}"
            if product.SKU:
                product_text += f" {product.SKU}"
            
            # メタデータを作成
            metadata = {
                "type": "product",
                "product_id": product.ProductID,
                "sku": product.SKU,
                "category_id": product.CategoryID,
                "price": product.Price,
                "stock_quantity": product.StockQuantity
            }
            
            # ベクトル検索を更新
            await self.vector_repository.update_document(
                collection_type="products",
                document_id=f"product_{product.ProductID}",
                document=product_text,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to update product in vector search: {e}")
    
    async def _remove_product_from_vector_search(self, product_id: int) -> None:
        """
        ベクトル検索から製品を削除
        
        Args:
            product_id: 製品ID
        """
        try:
            await self.vector_repository.delete_document(
                collection_type="products",
                document_id=f"product_{product_id}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to remove product from vector search: {e}")