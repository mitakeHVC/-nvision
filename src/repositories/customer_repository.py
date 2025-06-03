"""
顧客データリポジトリ

顧客データのCRUD操作を提供
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime

from .base import BaseRepository, EntityNotFoundError, DuplicateEntityError
from ..data_models.ec_models import Customer

logger = logging.getLogger(__name__)


class CustomerRepository(BaseRepository[Customer]):
    """
    顧客データリポジトリ
    
    顧客データの永続化とクエリ操作を提供
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        super().__init__()
        # インメモリストレージ（実際の実装ではデータベース接続を使用）
        self._customers: Dict[int, Customer] = {}
        self._next_id = 1
        
        # サンプルデータの初期化
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """サンプルデータの初期化"""
        sample_customers = [
            Customer(
                CustomerID=1,
                FirstName="田中",
                LastName="太郎",
                Email="tanaka@example.com",
                PhoneNumber="090-1234-5678",
                ShippingAddress="東京都渋谷区1-1-1",
                BillingAddress="東京都渋谷区1-1-1",
                RegistrationDate=datetime.now(),
                LastLoginDate=datetime.now()
            ),
            Customer(
                CustomerID=2,
                FirstName="佐藤",
                LastName="花子",
                Email="sato@example.com",
                PhoneNumber="090-2345-6789",
                ShippingAddress="大阪府大阪市2-2-2",
                BillingAddress="大阪府大阪市2-2-2",
                RegistrationDate=datetime.now(),
                LastLoginDate=datetime.now()
            ),
            Customer(
                CustomerID=3,
                FirstName="鈴木",
                LastName="一郎",
                Email="suzuki@example.com",
                PhoneNumber="090-3456-7890",
                ShippingAddress="愛知県名古屋市3-3-3",
                BillingAddress="愛知県名古屋市3-3-3",
                RegistrationDate=datetime.now(),
                LastLoginDate=datetime.now()
            )
        ]
        
        for customer in sample_customers:
            self._customers[customer.CustomerID] = customer
            self._next_id = max(self._next_id, customer.CustomerID + 1)
    
    async def create(self, entity: Customer) -> Customer:
        """顧客を作成"""
        try:
            self._log_operation("create_customer", email=entity.Email)
            
            # メールアドレスの重複チェック
            if entity.Email and await self.get_by_email(entity.Email):
                raise DuplicateEntityError(f"Customer with email {entity.Email} already exists")
            
            # IDが指定されていない場合は自動生成
            if not hasattr(entity, 'CustomerID') or entity.CustomerID is None:
                entity.CustomerID = self._next_id
                self._next_id += 1
            
            # 作成日時の設定
            if not entity.RegistrationDate:
                entity.RegistrationDate = datetime.now()
            
            self._customers[entity.CustomerID] = entity
            
            self.logger.info(f"Customer created successfully: {entity.CustomerID}")
            return entity
            
        except Exception as e:
            self._handle_error("create_customer", e)
    
    async def get_by_id(self, entity_id: UUID) -> Optional[Customer]:
        """IDで顧客を取得"""
        try:
            # UUIDをintに変換（実際の実装では適切な変換を行う）
            customer_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("get_customer_by_id", entity_id=entity_id)
            
            customer = self._customers.get(customer_id)
            if customer:
                self.logger.info(f"Customer found: {customer_id}")
            else:
                self.logger.info(f"Customer not found: {customer_id}")
            
            return customer
            
        except Exception as e:
            self._handle_error("get_customer_by_id", e, entity_id)
    
    async def get_by_customer_id(self, customer_id: int) -> Optional[Customer]:
        """顧客IDで顧客を取得"""
        try:
            self._log_operation("get_customer_by_customer_id", customer_id=customer_id)
            
            customer = self._customers.get(customer_id)
            if customer:
                self.logger.info(f"Customer found: {customer_id}")
            else:
                self.logger.info(f"Customer not found: {customer_id}")
            
            return customer
            
        except Exception as e:
            self._handle_error("get_customer_by_customer_id", e)
    
    async def get_by_email(self, email: str) -> Optional[Customer]:
        """メールアドレスで顧客を取得"""
        try:
            self._log_operation("get_customer_by_email", email=email)
            
            for customer in self._customers.values():
                if customer.Email == email:
                    self.logger.info(f"Customer found by email: {email}")
                    return customer
            
            self.logger.info(f"Customer not found by email: {email}")
            return None
            
        except Exception as e:
            self._handle_error("get_customer_by_email", e)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """全ての顧客を取得"""
        try:
            self._log_operation("get_all_customers", limit=limit, offset=offset)
            
            customers = list(self._customers.values())
            customers.sort(key=lambda x: x.CustomerID)
            
            result = customers[offset:offset + limit]
            
            self.logger.info(f"Retrieved {len(result)} customers")
            return result
            
        except Exception as e:
            self._handle_error("get_all_customers", e)
    
    async def update(self, entity_id: UUID, update_data: Dict[str, Any]) -> Optional[Customer]:
        """顧客を更新"""
        try:
            # UUIDをintに変換
            customer_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("update_customer", entity_id=entity_id, update_data=update_data)
            
            customer = self._customers.get(customer_id)
            if not customer:
                self.logger.warning(f"Customer not found for update: {customer_id}")
                return None
            
            # 更新データを適用
            customer_dict = customer.dict()
            customer_dict.update(update_data)
            
            # 更新された顧客エンティティを作成
            updated_customer = Customer(**customer_dict)
            self._customers[customer_id] = updated_customer
            
            self.logger.info(f"Customer updated successfully: {customer_id}")
            return updated_customer
            
        except Exception as e:
            self._handle_error("update_customer", e, entity_id)
    
    async def delete(self, entity_id: UUID) -> bool:
        """顧客を削除"""
        try:
            # UUIDをintに変換
            customer_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("delete_customer", entity_id=entity_id)
            
            if customer_id in self._customers:
                del self._customers[customer_id]
                self.logger.info(f"Customer deleted successfully: {customer_id}")
                return True
            else:
                self.logger.warning(f"Customer not found for deletion: {customer_id}")
                return False
                
        except Exception as e:
            self._handle_error("delete_customer", e, entity_id)
            return False
    
    async def exists(self, entity_id: UUID) -> bool:
        """顧客の存在確認"""
        try:
            # UUIDをintに変換
            customer_id = int(str(entity_id).split('-')[0], 16) % 1000000
            
            self._log_operation("customer_exists", entity_id=entity_id)
            
            exists = customer_id in self._customers
            self.logger.info(f"Customer exists check: {customer_id} -> {exists}")
            return exists
            
        except Exception as e:
            self._handle_error("customer_exists", e, entity_id)
            return False
    
    async def search_by_name(self, name: str) -> List[Customer]:
        """名前で顧客を検索"""
        try:
            self._log_operation("search_customers_by_name", name=name)
            
            results = []
            for customer in self._customers.values():
                full_name = f"{customer.FirstName or ''} {customer.LastName or ''}".strip()
                if name.lower() in full_name.lower():
                    results.append(customer)
            
            self.logger.info(f"Found {len(results)} customers matching name: {name}")
            return results
            
        except Exception as e:
            self._handle_error("search_customers_by_name", e)
            return []