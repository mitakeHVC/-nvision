"""
注文データリポジトリ

注文データのCRUD操作を提供
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime, timedelta

from .base import BaseRepository, EntityNotFoundError, DuplicateEntityError
from ..data_models.ec_models import Order, OrderItem

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[Order]):
    """
    注文データリポジトリ
    
    注文データの永続化とクエリ操作を提供
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        super().__init__()
        # インメモリストレージ（実際の実装ではデータベース接続を使用）
        self._orders: Dict[int, Order] = {}
        self._order_items: Dict[int, List[OrderItem]] = {}  # OrderID -> List[OrderItem]
        self._next_id = 1
        self._next_item_id = 1
        
        # サンプルデータの初期化
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """サンプルデータの初期化"""
        sample_orders = [
            Order(
                OrderID=1,
                CustomerID=1,
                OrderDate=datetime.now() - timedelta(days=5),
                OrderStatus="配送済み",
                TotalAmount=123500.0,
                ShippingAddress="東京都渋谷区1-1-1",
                BillingAddress="東京都渋谷区1-1-1"
            ),
            Order(
                OrderID=2,
                CustomerID=2,
                OrderDate=datetime.now() - timedelta(days=3),
                OrderStatus="処理中",
                TotalAmount=18500.0,
                ShippingAddress="大阪府大阪市2-2-2",
                BillingAddress="大阪府大阪市2-2-2"
            ),
            Order(
                OrderID=3,
                CustomerID=1,
                OrderDate=datetime.now() - timedelta(days=1),
                OrderStatus="発送準備中",
                TotalAmount=45000.0,
                ShippingAddress="東京都渋谷区1-1-1",
                BillingAddress="東京都渋谷区1-1-1"
            )
        ]
        
        sample_order_items = [
            # Order 1 items
            [
                OrderItem(OrderItemID=1, OrderID=1, ProductID=1, Quantity=1, UnitPrice=120000.0, TotalPrice=120000.0),
                OrderItem(OrderItemID=2, OrderID=1, ProductID=2, Quantity=1, UnitPrice=3500.0, TotalPrice=3500.0)
            ],
            # Order 2 items
            [
                OrderItem(OrderItemID=3, OrderID=2, ProductID=3, Quantity=1, UnitPrice=15000.0, TotalPrice=15000.0),
                OrderItem(OrderItemID=4, OrderID=2, ProductID=2, Quantity=1, UnitPrice=3500.0, TotalPrice=3500.0)
            ],
            # Order 3 items
            [
                OrderItem(OrderItemID=5, OrderID=3, ProductID=1, Quantity=1, UnitPrice=45000.0, TotalPrice=45000.0)
            ]
        ]
        
        for i, order in enumerate(sample_orders):
            self._orders[order.OrderID] = order
            self._order_items[order.OrderID] = sample_order_items[i]
            self._next_id = max(self._next_id, order.OrderID + 1)
        
        # 次のアイテムIDを設定
        for items in sample_order_items:
            for item in items:
                self._next_item_id = max(self._next_item_id, item.OrderItemID + 1)
    
    async def create(self, entity: Order) -> Order:
        """注文を作成"""
        try:
            self._log_operation("create_order", customer_id=entity.CustomerID)
            
            # IDが指定されていない場合は自動生成
            if not hasattr(entity, 'OrderID') or entity.OrderID is None:
                entity.OrderID = self._next_id
                self._next_id += 1
            
            # 注文日時の設定
            if not entity.OrderDate:
                entity.OrderDate = datetime.now()
            
            # デフォルトステータスの設定
            if not entity.OrderStatus:
                entity.OrderStatus = "注文確認中"
            
            self._orders[entity.OrderID] = entity
            self._order_items[entity.OrderID] = []  # 空の注文アイテムリストを初期化
            
            self.logger.info(f"Order created successfully: {entity.OrderID}")
            return entity
            
        except Exception as e:
            self._handle_error("create_order", e)
    
    async def get_by_id(self, entity_id: UUID) -> Optional[Order]:
        """IDで注文を取得"""
        try:
            # UUIDをintに変換（実際の実装では適切な変換を行う）
            order_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("get_order_by_id", entity_id=entity_id)
            
            order = self._orders.get(order_id)
            if order:
                self.logger.info(f"Order found: {order_id}")
            else:
                self.logger.info(f"Order not found: {order_id}")
            
            return order
            
        except Exception as e:
            self._handle_error("get_order_by_id", e, entity_id)
    
    async def get_by_order_id(self, order_id: int) -> Optional[Order]:
        """注文IDで注文を取得"""
        try:
            self._log_operation("get_order_by_order_id", order_id=order_id)
            
            order = self._orders.get(order_id)
            if order:
                self.logger.info(f"Order found: {order_id}")
            else:
                self.logger.info(f"Order not found: {order_id}")
            
            return order
            
        except Exception as e:
            self._handle_error("get_order_by_order_id", e)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Order]:
        """全ての注文を取得"""
        try:
            self._log_operation("get_all_orders", limit=limit, offset=offset)
            
            orders = list(self._orders.values())
            orders.sort(key=lambda x: x.OrderDate or datetime.min, reverse=True)
            
            result = orders[offset:offset + limit]
            
            self.logger.info(f"Retrieved {len(result)} orders")
            return result
            
        except Exception as e:
            self._handle_error("get_all_orders", e)
    
    async def update(self, entity_id: UUID, update_data: Dict[str, Any]) -> Optional[Order]:
        """注文を更新"""
        try:
            # UUIDをintに変換
            order_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("update_order", entity_id=entity_id, update_data=update_data)
            
            order = self._orders.get(order_id)
            if not order:
                self.logger.warning(f"Order not found for update: {order_id}")
                return None
            
            # 更新データを適用
            order_dict = order.dict()
            order_dict.update(update_data)
            
            # 更新された注文エンティティを作成
            updated_order = Order(**order_dict)
            self._orders[order_id] = updated_order
            
            self.logger.info(f"Order updated successfully: {order_id}")
            return updated_order
            
        except Exception as e:
            self._handle_error("update_order", e, entity_id)
    
    async def delete(self, entity_id: UUID) -> bool:
        """注文を削除"""
        try:
            # UUIDをintに変換
            order_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("delete_order", entity_id=entity_id)
            
            if order_id in self._orders:
                del self._orders[order_id]
                # 関連する注文アイテムも削除
                if order_id in self._order_items:
                    del self._order_items[order_id]
                self.logger.info(f"Order deleted successfully: {order_id}")
                return True
            else:
                self.logger.warning(f"Order not found for deletion: {order_id}")
                return False
                
        except Exception as e:
            self._handle_error("delete_order", e, entity_id)
            return False
    
    async def exists(self, entity_id: UUID) -> bool:
        """注文の存在確認"""
        try:
            # UUIDをintに変換
            order_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("order_exists", entity_id=entity_id)
            
            exists = order_id in self._orders
            self.logger.info(f"Order exists check: {order_id} -> {exists}")
            return exists
            
        except Exception as e:
            self._handle_error("order_exists", e, entity_id)
            return False
    
    async def get_by_customer_id(self, customer_id: int) -> List[Order]:
        """顧客IDで注文を取得"""
        try:
            self._log_operation("get_orders_by_customer", customer_id=customer_id)
            
            results = []
            for order in self._orders.values():
                if order.CustomerID == customer_id:
                    results.append(order)
            
            # 注文日時の降順でソート
            results.sort(key=lambda x: x.OrderDate or datetime.min, reverse=True)
            
            self.logger.info(f"Found {len(results)} orders for customer: {customer_id}")
            return results
            
        except Exception as e:
            self._handle_error("get_orders_by_customer", e)
            return []
    
    async def get_by_status(self, status: str) -> List[Order]:
        """ステータスで注文を取得"""
        try:
            self._log_operation("get_orders_by_status", status=status)
            
            results = []
            for order in self._orders.values():
                if order.OrderStatus == status:
                    results.append(order)
            
            # 注文日時の降順でソート
            results.sort(key=lambda x: x.OrderDate or datetime.min, reverse=True)
            
            self.logger.info(f"Found {len(results)} orders with status: {status}")
            return results
            
        except Exception as e:
            self._handle_error("get_orders_by_status", e)
            return []
    
    async def get_order_items(self, order_id: int) -> List[OrderItem]:
        """注文アイテムを取得"""
        try:
            self._log_operation("get_order_items", order_id=order_id)
            
            items = self._order_items.get(order_id, [])
            
            self.logger.info(f"Found {len(items)} items for order: {order_id}")
            return items
            
        except Exception as e:
            self._handle_error("get_order_items", e)
            return []
    
    async def add_order_item(self, order_id: int, item: OrderItem) -> OrderItem:
        """注文アイテムを追加"""
        try:
            self._log_operation("add_order_item", order_id=order_id, product_id=item.ProductID)
            
            # 注文の存在確認
            if order_id not in self._orders:
                raise EntityNotFoundError(f"Order {order_id} not found")
            
            # アイテムIDの設定
            if not hasattr(item, 'OrderItemID') or item.OrderItemID is None:
                item.OrderItemID = self._next_item_id
                self._next_item_id += 1
            
            # 注文IDの設定
            item.OrderID = order_id
            
            # 注文アイテムリストに追加
            if order_id not in self._order_items:
                self._order_items[order_id] = []
            
            self._order_items[order_id].append(item)
            
            self.logger.info(f"Order item added successfully: {item.OrderItemID}")
            return item
            
        except Exception as e:
            self._handle_error("add_order_item", e)