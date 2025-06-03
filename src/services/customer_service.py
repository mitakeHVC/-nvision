"""
顧客ビジネスロジックサービス

顧客に関するビジネスロジックを提供
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from ..repositories.customer_repository import CustomerRepository
from ..repositories.vector_repository import VectorRepository
from ..data_models.ec_models import Customer

logger = logging.getLogger(__name__)


class CustomerService:
    """
    顧客ビジネスロジックサービス
    
    顧客データの操作とビジネスルールの実装
    """
    
    def __init__(self):
        """サービスの初期化"""
        self.customer_repository = CustomerRepository()
        self.vector_repository = VectorRepository()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> Customer:
        """
        新しい顧客を作成
        
        Args:
            customer_data: 顧客データ
            
        Returns:
            作成された顧客エンティティ
            
        Raises:
            ValueError: 無効なデータの場合
            DuplicateEntityError: 重複する顧客の場合
        """
        try:
            self.logger.info(f"Creating new customer: {customer_data.get('Email')}")
            
            # データ検証
            self._validate_customer_data(customer_data)
            
            # 顧客エンティティを作成
            customer = Customer(**customer_data)
            
            # リポジトリに保存
            created_customer = await self.customer_repository.create(customer)
            
            # ベクトル検索用のドキュメントを作成
            await self._add_customer_to_vector_search(created_customer)
            
            self.logger.info(f"Customer created successfully: {created_customer.CustomerID}")
            return created_customer
            
        except Exception as e:
            self.logger.error(f"Failed to create customer: {e}")
            raise
    
    async def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """
        IDで顧客を取得
        
        Args:
            customer_id: 顧客ID
            
        Returns:
            顧客エンティティまたはNone
        """
        try:
            self.logger.info(f"Getting customer by ID: {customer_id}")
            
            customer = await self.customer_repository.get_by_customer_id(customer_id)
            
            if customer:
                self.logger.info(f"Customer found: {customer_id}")
            else:
                self.logger.info(f"Customer not found: {customer_id}")
            
            return customer
            
        except Exception as e:
            self.logger.error(f"Failed to get customer by ID {customer_id}: {e}")
            raise
    
    async def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """
        メールアドレスで顧客を取得
        
        Args:
            email: メールアドレス
            
        Returns:
            顧客エンティティまたはNone
        """
        try:
            self.logger.info(f"Getting customer by email: {email}")
            
            customer = await self.customer_repository.get_by_email(email)
            
            if customer:
                self.logger.info(f"Customer found by email: {email}")
            else:
                self.logger.info(f"Customer not found by email: {email}")
            
            return customer
            
        except Exception as e:
            self.logger.error(f"Failed to get customer by email {email}: {e}")
            raise
    
    async def get_all_customers(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """
        全ての顧客を取得
        
        Args:
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            顧客エンティティのリスト
        """
        try:
            self.logger.info(f"Getting all customers: limit={limit}, offset={offset}")
            
            customers = await self.customer_repository.get_all(limit=limit, offset=offset)
            
            self.logger.info(f"Retrieved {len(customers)} customers")
            return customers
            
        except Exception as e:
            self.logger.error(f"Failed to get all customers: {e}")
            raise
    
    async def update_customer(self, customer_id: int, update_data: Dict[str, Any]) -> Optional[Customer]:
        """
        顧客情報を更新
        
        Args:
            customer_id: 顧客ID
            update_data: 更新データ
            
        Returns:
            更新された顧客エンティティまたはNone
        """
        try:
            self.logger.info(f"Updating customer: {customer_id}")
            
            # 既存の顧客を確認
            existing_customer = await self.customer_repository.get_by_customer_id(customer_id)
            if not existing_customer:
                self.logger.warning(f"Customer not found for update: {customer_id}")
                return None
            
            # データ検証
            self._validate_update_data(update_data)
            
            # UUIDを生成（リポジトリのメソッドに合わせる）
            from uuid import uuid4
            entity_id = uuid4()
            
            # 更新実行
            updated_customer = await self.customer_repository.update(entity_id, update_data)
            
            if updated_customer:
                # ベクトル検索のドキュメントも更新
                await self._update_customer_in_vector_search(updated_customer)
                self.logger.info(f"Customer updated successfully: {customer_id}")
            
            return updated_customer
            
        except Exception as e:
            self.logger.error(f"Failed to update customer {customer_id}: {e}")
            raise
    
    async def delete_customer(self, customer_id: int) -> bool:
        """
        顧客を削除
        
        Args:
            customer_id: 顧客ID
            
        Returns:
            削除成功の場合True
        """
        try:
            self.logger.info(f"Deleting customer: {customer_id}")
            
            # 既存の顧客を確認
            existing_customer = await self.customer_repository.get_by_customer_id(customer_id)
            if not existing_customer:
                self.logger.warning(f"Customer not found for deletion: {customer_id}")
                return False
            
            # UUIDを生成（リポジトリのメソッドに合わせる）
            from uuid import uuid4
            entity_id = uuid4()
            
            # 削除実行
            success = await self.customer_repository.delete(entity_id)
            
            if success:
                # ベクトル検索からも削除
                await self._remove_customer_from_vector_search(customer_id)
                self.logger.info(f"Customer deleted successfully: {customer_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete customer {customer_id}: {e}")
            raise
    
    async def search_customers_by_name(self, name: str) -> List[Customer]:
        """
        名前で顧客を検索
        
        Args:
            name: 検索する名前
            
        Returns:
            マッチした顧客エンティティのリスト
        """
        try:
            self.logger.info(f"Searching customers by name: {name}")
            
            customers = await self.customer_repository.search_by_name(name)
            
            self.logger.info(f"Found {len(customers)} customers matching name: {name}")
            return customers
            
        except Exception as e:
            self.logger.error(f"Failed to search customers by name {name}: {e}")
            raise
    
    async def get_recent_customers(self, days: int = 30) -> List[Customer]:
        """
        最近登録された顧客を取得
        
        Args:
            days: 過去何日間の顧客を取得するか
            
        Returns:
            最近登録された顧客エンティティのリスト
        """
        try:
            self.logger.info(f"Getting recent customers: last {days} days")
            
            customers = await self.customer_repository.get_recent_customers(days=days)
            
            self.logger.info(f"Found {len(customers)} recent customers")
            return customers
            
        except Exception as e:
            self.logger.error(f"Failed to get recent customers: {e}")
            raise
    
    async def get_customer_statistics(self) -> Dict[str, Any]:
        """
        顧客統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        try:
            self.logger.info("Getting customer statistics")
            
            # 全顧客数
            all_customers = await self.customer_repository.get_all()
            total_customers = len(all_customers)
            
            # 最近30日間の新規顧客数
            recent_customers = await self.get_recent_customers(30)
            recent_count = len(recent_customers)
            
            # 統計情報を作成
            stats = {
                "total_customers": total_customers,
                "recent_customers_30_days": recent_count,
                "growth_rate": (recent_count / total_customers * 100) if total_customers > 0 else 0,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Customer statistics generated: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get customer statistics: {e}")
            raise
    
    def _validate_customer_data(self, customer_data: Dict[str, Any]) -> None:
        """
        顧客データの検証
        
        Args:
            customer_data: 検証する顧客データ
            
        Raises:
            ValueError: 無効なデータの場合
        """
        required_fields = ['FirstName', 'LastName', 'Email']
        
        for field in required_fields:
            if not customer_data.get(field):
                raise ValueError(f"Required field missing: {field}")
        
        # メールアドレスの簡単な検証
        email = customer_data.get('Email')
        if email and '@' not in email:
            raise ValueError("Invalid email format")
    
    def _validate_update_data(self, update_data: Dict[str, Any]) -> None:
        """
        更新データの検証
        
        Args:
            update_data: 検証する更新データ
            
        Raises:
            ValueError: 無効なデータの場合
        """
        # メールアドレスが含まれている場合は検証
        email = update_data.get('Email')
        if email and '@' not in email:
            raise ValueError("Invalid email format")
    
    async def _add_customer_to_vector_search(self, customer: Customer) -> None:
        """
        顧客をベクトル検索に追加
        
        Args:
            customer: 顧客エンティティ
        """
        try:
            # 顧客情報をテキスト化
            customer_text = f"{customer.FirstName} {customer.LastName} {customer.Email}"
            if customer.ShippingAddress:
                customer_text += f" {customer.ShippingAddress}"
            
            # メタデータを作成
            metadata = {
                "type": "customer",
                "customer_id": customer.CustomerID,
                "email": customer.Email,
                "registration_date": customer.RegistrationDate.isoformat() if customer.RegistrationDate else None
            }
            
            # ベクトル検索に追加
            await self.vector_repository.add_document(
                collection_type="customers",
                document=customer_text,
                metadata=metadata,
                document_id=f"customer_{customer.CustomerID}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to add customer to vector search: {e}")
    
    async def _update_customer_in_vector_search(self, customer: Customer) -> None:
        """
        ベクトル検索の顧客情報を更新
        
        Args:
            customer: 顧客エンティティ
        """
        try:
            # 顧客情報をテキスト化
            customer_text = f"{customer.FirstName} {customer.LastName} {customer.Email}"
            if customer.ShippingAddress:
                customer_text += f" {customer.ShippingAddress}"
            
            # メタデータを作成
            metadata = {
                "type": "customer",
                "customer_id": customer.CustomerID,
                "email": customer.Email,
                "registration_date": customer.RegistrationDate.isoformat() if customer.RegistrationDate else None
            }
            
            # ベクトル検索を更新
            await self.vector_repository.update_document(
                collection_type="customers",
                document_id=f"customer_{customer.CustomerID}",
                document=customer_text,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to update customer in vector search: {e}")
    
    async def _remove_customer_from_vector_search(self, customer_id: int) -> None:
        """
        ベクトル検索から顧客を削除
        
        Args:
            customer_id: 顧客ID
        """
        try:
            await self.vector_repository.delete_document(
                collection_type="customers",
                document_id=f"customer_{customer_id}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to remove customer from vector search: {e}")