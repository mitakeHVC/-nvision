"""
注文ビジネスロジックサービス

注文に関するビジネスロジックを提供
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from ..repositories.order_repository import OrderRepository
from ..repositories.customer_repository import CustomerRepository
from ..repositories.product_repository import ProductRepository
from ..data_models.ec_models import Order, OrderItem

logger = logging.getLogger(__name__)


class OrderService:
    """
    注文ビジネスロジックサービス
    
    注文データの操作とビジネスルールの実装
    """
    
    def __init__(self):
        """サービスの初期化"""
        self.order_repository = OrderRepository()
        self.customer_repository = CustomerRepository()
        self.product_repository = ProductRepository()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def create_order(self, order_data: Dict[str, Any]) -> Order:
        """
        新しい注文を作成
        
        Args:
            order_data: 注文データ
            
        Returns:
            作成された注文エンティティ
            
        Raises:
            ValueError: 無効なデータの場合
            EntityNotFoundError: 顧客が見つからない場合
        """
        try:
            self.logger.info(f"Creating new order for customer: {order_data.get('CustomerID')}")
            
            # データ検証
            await self._validate_order_data(order_data)
            
            # 注文エンティティを作成
            order = Order(**order_data)
            
            # リポジトリに保存
            created_order = await self.order_repository.create(order)
            
            self.logger.info(f"Order created successfully: {created_order.OrderID}")
            return created_order
            
        except Exception as e:
            self.logger.error(f"Failed to create order: {e}")
            raise
    
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """
        IDで注文を取得
        
        Args:
            order_id: 注文ID
            
        Returns:
            注文エンティティまたはNone
        """
        try:
            self.logger.info(f"Getting order by ID: {order_id}")
            
            order = await self.order_repository.get_by_order_id(order_id)
            
            if order:
                self.logger.info(f"Order found: {order_id}")
            else:
                self.logger.info(f"Order not found: {order_id}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to get order by ID {order_id}: {e}")
            raise
    
    async def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        """
        顧客IDで注文を取得
        
        Args:
            customer_id: 顧客ID
            
        Returns:
            顧客の注文エンティティのリスト
        """
        try:
            self.logger.info(f"Getting orders for customer: {customer_id}")
            
            orders = await self.order_repository.get_by_customer_id(customer_id)
            
            self.logger.info(f"Found {len(orders)} orders for customer: {customer_id}")
            return orders
            
        except Exception as e:
            self.logger.error(f"Failed to get orders for customer {customer_id}: {e}")
            raise
    
    async def get_orders_by_status(self, status: str) -> List[Order]:
        """
        ステータスで注文を取得
        
        Args:
            status: 注文ステータス
            
        Returns:
            指定ステータスの注文エンティティのリスト
        """
        try:
            self.logger.info(f"Getting orders by status: {status}")
            
            orders = await self.order_repository.get_by_status(status)
            
            self.logger.info(f"Found {len(orders)} orders with status: {status}")
            return orders
            
        except Exception as e:
            self.logger.error(f"Failed to get orders by status {status}: {e}")
            raise
    
    async def get_all_orders(self, limit: int = 100, offset: int = 0) -> List[Order]:
        """
        全ての注文を取得
        
        Args:
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            注文エンティティのリスト
        """
        try:
            self.logger.info(f"Getting all orders: limit={limit}, offset={offset}")
            
            orders = await self.order_repository.get_all(limit=limit, offset=offset)
            
            self.logger.info(f"Retrieved {len(orders)} orders")
            return orders
            
        except Exception as e:
            self.logger.error(f"Failed to get all orders: {e}")
            raise
    
    async def update_order_status(self, order_id: int, status: str) -> Optional[Order]:
        """
        注文ステータスを更新
        
        Args:
            order_id: 注文ID
            status: 新しいステータス
            
        Returns:
            更新された注文エンティティまたはNone
        """
        try:
            self.logger.info(f"Updating order status: {order_id} -> {status}")
            
            # ステータス検証
            self._validate_order_status(status)
            
            # 更新実行
            updated_order = await self.order_repository.update_order_status(order_id, status)
            
            if updated_order:
                self.logger.info(f"Order status updated successfully: {order_id}")
                
                # ステータス変更に応じた追加処理
                await self._handle_status_change(updated_order, status)
            
            return updated_order
            
        except Exception as e:
            self.logger.error(f"Failed to update order status {order_id}: {e}")
            raise
    
    async def add_order_item(self, order_id: int, item_data: Dict[str, Any]) -> OrderItem:
        """
        注文アイテムを追加
        
        Args:
            order_id: 注文ID
            item_data: 注文アイテムデータ
            
        Returns:
            追加された注文アイテム
            
        Raises:
            ValueError: 無効なデータの場合
            EntityNotFoundError: 注文または製品が見つからない場合
        """
        try:
            self.logger.info(f"Adding item to order {order_id}: {item_data}")
            
            # データ検証
            await self._validate_order_item_data(item_data)
            
            # 製品の在庫確認
            product_id = item_data['ProductID']
            quantity = item_data['Quantity']
            
            product = await self.product_repository.get_by_product_id(product_id)
            if not product:
                raise ValueError(f"Product not found: {product_id}")
            
            if product.StockQuantity is not None and product.StockQuantity < quantity:
                raise ValueError(f"Insufficient stock for product {product_id}")
            
            # 価格計算
            unit_price = product.Price or 0
            total_price = unit_price * quantity
            
            # 注文アイテムを作成
            item_data.update({
                'UnitPrice': unit_price,
                'TotalPrice': total_price
            })
            
            order_item = OrderItem(**item_data)
            
            # リポジトリに追加
            added_item = await self.order_repository.add_order_item(order_id, order_item)
            
            # 在庫を減らす
            await self.product_repository.update_stock(product_id, -quantity)
            
            # 注文の合計金額を更新
            await self._update_order_total(order_id)
            
            self.logger.info(f"Order item added successfully: {added_item.OrderItemID}")
            return added_item
            
        except Exception as e:
            self.logger.error(f"Failed to add order item: {e}")
            raise
    
    async def get_order_items(self, order_id: int) -> List[OrderItem]:
        """
        注文アイテムを取得
        
        Args:
            order_id: 注文ID
            
        Returns:
            注文アイテムのリスト
        """
        try:
            self.logger.info(f"Getting order items for order: {order_id}")
            
            items = await self.order_repository.get_order_items(order_id)
            
            self.logger.info(f"Found {len(items)} items for order: {order_id}")
            return items
            
        except Exception as e:
            self.logger.error(f"Failed to get order items for order {order_id}: {e}")
            raise
    
    async def get_order_with_items(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        注文と注文アイテムを一緒に取得
        
        Args:
            order_id: 注文ID
            
        Returns:
            注文と注文アイテムを含む辞書またはNone
        """
        try:
            self.logger.info(f"Getting order with items: {order_id}")
            
            # 注文を取得
            order = await self.get_order_by_id(order_id)
            if not order:
                return None
            
            # 注文アイテムを取得
            items = await self.get_order_items(order_id)
            
            # 顧客情報を取得
            customer = None
            if order.CustomerID:
                customer = await self.customer_repository.get_by_customer_id(order.CustomerID)
            
            result = {
                "order": order,
                "items": items,
                "customer": customer,
                "item_count": len(items)
            }
            
            self.logger.info(f"Order with items retrieved: {order_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get order with items {order_id}: {e}")
            raise
    
    async def cancel_order(self, order_id: int, reason: str = "") -> bool:
        """
        注文をキャンセル
        
        Args:
            order_id: 注文ID
            reason: キャンセル理由
            
        Returns:
            キャンセル成功の場合True
        """
        try:
            self.logger.info(f"Cancelling order: {order_id}, reason: {reason}")
            
            # 注文を取得
            order = await self.get_order_by_id(order_id)
            if not order:
                self.logger.warning(f"Order not found for cancellation: {order_id}")
                return False
            
            # キャンセル可能かチェック
            if order.OrderStatus in ["配送済み", "完了"]:
                raise ValueError(f"Cannot cancel order with status: {order.OrderStatus}")
            
            # 在庫を戻す
            items = await self.get_order_items(order_id)
            for item in items:
                if item.ProductID and item.Quantity:
                    await self.product_repository.update_stock(item.ProductID, item.Quantity)
            
            # ステータスを更新
            await self.update_order_status(order_id, "キャンセル")
            
            self.logger.info(f"Order cancelled successfully: {order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
    
    async def get_order_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        注文統計情報を取得
        
        Args:
            days: 統計期間（日数）
            
        Returns:
            統計情報の辞書
        """
        try:
            self.logger.info(f"Getting order statistics for last {days} days")
            
            # 期間の設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 期間内の注文を取得
            orders = await self.order_repository.get_by_date_range(start_date, end_date)
            
            # 統計計算
            total_orders = len(orders)
            total_amount = sum(order.TotalAmount or 0 for order in orders)
            avg_order_value = total_amount / total_orders if total_orders > 0 else 0
            
            # ステータス別集計
            status_counts = {}
            for order in orders:
                status = order.OrderStatus or "未設定"
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # 日別集計
            daily_orders = {}
            for order in orders:
                if order.OrderDate:
                    date_key = order.OrderDate.date().isoformat()
                    daily_orders[date_key] = daily_orders.get(date_key, 0) + 1
            
            stats = {
                "period_days": days,
                "total_orders": total_orders,
                "total_amount": total_amount,
                "average_order_value": avg_order_value,
                "status_breakdown": status_counts,
                "daily_orders": daily_orders,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Order statistics generated: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get order statistics: {e}")
            raise
    
    async def _validate_order_data(self, order_data: Dict[str, Any]) -> None:
        """
        注文データの検証
        
        Args:
            order_data: 検証する注文データ
            
        Raises:
            ValueError: 無効なデータの場合
        """
        # 顧客IDの検証
        customer_id = order_data.get('CustomerID')
        if customer_id:
            customer = await self.customer_repository.get_by_customer_id(customer_id)
            if not customer:
                raise ValueError(f"Customer not found: {customer_id}")
        
        # 金額の検証
        total_amount = order_data.get('TotalAmount')
        if total_amount is not None and total_amount < 0:
            raise ValueError("Total amount cannot be negative")
    
    async def _validate_order_item_data(self, item_data: Dict[str, Any]) -> None:
        """
        注文アイテムデータの検証
        
        Args:
            item_data: 検証する注文アイテムデータ
            
        Raises:
            ValueError: 無効なデータの場合
        """
        required_fields = ['ProductID', 'Quantity']
        
        for field in required_fields:
            if not item_data.get(field):
                raise ValueError(f"Required field missing: {field}")
        
        # 数量の検証
        quantity = item_data.get('Quantity')
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
    
    def _validate_order_status(self, status: str) -> None:
        """
        注文ステータスの検証
        
        Args:
            status: 検証するステータス
            
        Raises:
            ValueError: 無効なステータスの場合
        """
        valid_statuses = [
            "注文確認中", "処理中", "発送準備中", "発送済み", "配送中", "配送済み", "完了", "キャンセル"
        ]
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid order status: {status}")
    
    async def _update_order_total(self, order_id: int) -> None:
        """
        注文の合計金額を更新
        
        Args:
            order_id: 注文ID
        """
        try:
            # 注文アイテムの合計を計算
            total_amount = await self.order_repository.calculate_total_amount(order_id)
            
            # 注文を更新
            from uuid import uuid4
            entity_id = uuid4()
            
            await self.order_repository.update(entity_id, {"TotalAmount": total_amount})
            
        except Exception as e:
            self.logger.warning(f"Failed to update order total for {order_id}: {e}")
    
    async def _handle_status_change(self, order: Order, new_status: str) -> None:
        """
        ステータス変更に応じた追加処理
        
        Args:
            order: 注文エンティティ
            new_status: 新しいステータス
        """
        try:
            if new_status == "発送済み":
                self.logger.info(f"Order shipped: {order.OrderID}")
                # 発送通知などの処理をここに追加
            
            elif new_status == "配送済み":
                self.logger.info(f"Order delivered: {order.OrderID}")
                # 配送完了通知などの処理をここに追加
            
            elif new_status == "キャンセル":
                self.logger.info(f"Order cancelled: {order.OrderID}")
                # キャンセル通知などの処理をここに追加
            
        except Exception as e:
            self.logger.warning(f"Failed to handle status change for order {order.OrderID}: {e}")