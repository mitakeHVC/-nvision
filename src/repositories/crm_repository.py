"""
CRMデータリポジトリ

CRMデータのCRUD操作を提供
"""

from typing import List, Optional, Dict, Any, Union
from uuid import UUID
import logging
from datetime import datetime, timedelta

from .base import BaseRepository, EntityNotFoundError, DuplicateEntityError
from ..data_models.crm_models import Contact, Company, Interaction, Deal, User

logger = logging.getLogger(__name__)


class CRMRepository(BaseRepository[Union[Contact, Company, Interaction, Deal, User]]):
    """
    CRMデータリポジトリ
    
    CRMデータの永続化とクエリ操作を提供
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        super().__init__()
        # インメモリストレージ（実際の実装ではデータベース接続を使用）
        self._contacts: Dict[int, Contact] = {}
        self._companies: Dict[int, Company] = {}
        self._interactions: Dict[int, Interaction] = {}
        self._deals: Dict[int, Deal] = {}
        self._users: Dict[int, User] = {}
        
        self._next_contact_id = 1
        self._next_company_id = 1
        self._next_interaction_id = 1
        self._next_deal_id = 1
        self._next_user_id = 1
        
        # サンプルデータの初期化
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """サンプルデータの初期化"""
        # ユーザー（営業担当者）
        sample_users = [
            User(UserID=1, FirstName="営業", LastName="太郎", Email="sales1@company.com"),
            User(UserID=2, FirstName="営業", LastName="花子", Email="sales2@company.com"),
            User(UserID=3, FirstName="営業", LastName="次郎", Email="sales3@company.com")
        ]
        
        # 会社
        sample_companies = [
            Company(
                CompanyID=1,
                CompanyName="株式会社テクノロジー",
                Industry="IT・ソフトウェア",
                Website="https://technology.co.jp",
                Address="東京都港区1-1-1",
                PhoneNumber="03-1234-5678",
                AnnualRevenue=500000000.0,
                NumberOfEmployees=100
            ),
            Company(
                CompanyID=2,
                CompanyName="製造業株式会社",
                Industry="製造業",
                Website="https://manufacturing.co.jp",
                Address="大阪府大阪市2-2-2",
                PhoneNumber="06-2345-6789",
                AnnualRevenue=1000000000.0,
                NumberOfEmployees=500
            )
        ]
        
        # 連絡先
        sample_contacts = [
            Contact(
                ContactID=1,
                FirstName="田中",
                LastName="太郎",
                Email="tanaka@technology.co.jp",
                PhoneNumber="03-1234-5678",
                JobTitle="CTO",
                CompanyID=1,
                LeadSource="ウェブサイト",
                DateCreated=datetime.now() - timedelta(days=30),
                LastContactedDate=datetime.now() - timedelta(days=5)
            ),
            Contact(
                ContactID=2,
                FirstName="佐藤",
                LastName="花子",
                Email="sato@manufacturing.co.jp",
                PhoneNumber="06-2345-6789",
                JobTitle="購買部長",
                CompanyID=2,
                LeadSource="展示会",
                DateCreated=datetime.now() - timedelta(days=20),
                LastContactedDate=datetime.now() - timedelta(days=2)
            )
        ]
        
        # 商談
        sample_deals = [
            Deal(
                DealID=1,
                DealName="システム導入プロジェクト",
                CompanyID=1,
                PrimaryContactID=1,
                Stage="提案",
                Amount=5000000.0,
                ExpectedCloseDate=datetime.now() + timedelta(days=30),
                AssignedToUserID=1
            ),
            Deal(
                DealID=2,
                DealName="製造ライン自動化",
                CompanyID=2,
                PrimaryContactID=2,
                Stage="交渉",
                Amount=10000000.0,
                ExpectedCloseDate=datetime.now() + timedelta(days=60),
                AssignedToUserID=2
            )
        ]
        
        # インタラクション
        sample_interactions = [
            Interaction(
                InteractionID=1,
                ContactID=1,
                CompanyID=1,
                InteractionType="メール",
                InteractionDate=datetime.now() - timedelta(days=5),
                Subject="システム導入についてのフォローアップ",
                Notes="要件定義の詳細について議論。次回ミーティングを設定。",
                AssignedToUserID=1
            ),
            Interaction(
                InteractionID=2,
                ContactID=2,
                CompanyID=2,
                InteractionType="電話",
                InteractionDate=datetime.now() - timedelta(days=2),
                Subject="製造ライン自動化の進捗確認",
                Notes="技術的な課題について相談。エンジニアとの打ち合わせが必要。",
                AssignedToUserID=2
            )
        ]
        
        # データを格納
        for user in sample_users:
            self._users[user.UserID] = user
            self._next_user_id = max(self._next_user_id, user.UserID + 1)
        
        for company in sample_companies:
            self._companies[company.CompanyID] = company
            self._next_company_id = max(self._next_company_id, company.CompanyID + 1)
        
        for contact in sample_contacts:
            self._contacts[contact.ContactID] = contact
            self._next_contact_id = max(self._next_contact_id, contact.ContactID + 1)
        
        for deal in sample_deals:
            self._deals[deal.DealID] = deal
            self._next_deal_id = max(self._next_deal_id, deal.DealID + 1)
        
        for interaction in sample_interactions:
            self._interactions[interaction.InteractionID] = interaction
            self._next_interaction_id = max(self._next_interaction_id, interaction.InteractionID + 1)
    
    async def create(self, entity: Union[Contact, Company, Interaction, Deal, User]) -> Union[Contact, Company, Interaction, Deal, User]:
        """CRMエンティティを作成"""
        try:
            entity_type = type(entity).__name__
            self._log_operation(f"create_{entity_type.lower()}")
            
            if isinstance(entity, Contact):
                return await self._create_contact(entity)
            elif isinstance(entity, Company):
                return await self._create_company(entity)
            elif isinstance(entity, Interaction):
                return await self._create_interaction(entity)
            elif isinstance(entity, Deal):
                return await self._create_deal(entity)
            elif isinstance(entity, User):
                return await self._create_user(entity)
            else:
                raise ValueError(f"Unsupported entity type: {entity_type}")
                
        except Exception as e:
            self._handle_error("create_crm_entity", e)
    
    async def _create_contact(self, contact: Contact) -> Contact:
        """連絡先を作成"""
        if not hasattr(contact, 'ContactID') or contact.ContactID is None:
            contact.ContactID = self._next_contact_id
            self._next_contact_id += 1
        
        if not contact.DateCreated:
            contact.DateCreated = datetime.now()
        
        self._contacts[contact.ContactID] = contact
        self.logger.info(f"Contact created: {contact.ContactID}")
        return contact
    
    async def _create_company(self, company: Company) -> Company:
        """会社を作成"""
        if not hasattr(company, 'CompanyID') or company.CompanyID is None:
            company.CompanyID = self._next_company_id
            self._next_company_id += 1
        
        self._companies[company.CompanyID] = company
        self.logger.info(f"Company created: {company.CompanyID}")
        return company
    
    async def _create_interaction(self, interaction: Interaction) -> Interaction:
        """インタラクションを作成"""
        if not hasattr(interaction, 'InteractionID') or interaction.InteractionID is None:
            interaction.InteractionID = self._next_interaction_id
            self._next_interaction_id += 1
        
        if not interaction.InteractionDate:
            interaction.InteractionDate = datetime.now()
        
        self._interactions[interaction.InteractionID] = interaction
        self.logger.info(f"Interaction created: {interaction.InteractionID}")
        return interaction
    
    async def _create_deal(self, deal: Deal) -> Deal:
        """商談を作成"""
        if not hasattr(deal, 'DealID') or deal.DealID is None:
            deal.DealID = self._next_deal_id
            self._next_deal_id += 1
        
        self._deals[deal.DealID] = deal
        self.logger.info(f"Deal created: {deal.DealID}")
        return deal
    
    async def _create_user(self, user: User) -> User:
        """ユーザーを作成"""
        if not hasattr(user, 'UserID') or user.UserID is None:
            user.UserID = self._next_user_id
            self._next_user_id += 1
        
        self._users[user.UserID] = user
        self.logger.info(f"User created: {user.UserID}")
        return user
    
    async def get_by_id(self, entity_id: UUID) -> Optional[Union[Contact, Company, Interaction, Deal, User]]:
        """IDでエンティティを取得（汎用メソッド）"""
        try:
            # UUIDをintに変換
            id_value = int(str(entity_id).split('-')[0], 16) % 1000000
            
            # 各タイプで検索
            if id_value in self._contacts:
                return self._contacts[id_value]
            elif id_value in self._companies:
                return self._companies[id_value]
            elif id_value in self._interactions:
                return self._interactions[id_value]
            elif id_value in self._deals:
                return self._deals[id_value]
            elif id_value in self._users:
                return self._users[id_value]
            
            return None
            
        except Exception as e:
            self._handle_error("get_crm_entity_by_id", e, entity_id)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Union[Contact, Company, Interaction, Deal, User]]:
        """全てのエンティティを取得（汎用メソッド）"""
        try:
            all_entities = []
            all_entities.extend(self._contacts.values())
            all_entities.extend(self._companies.values())
            all_entities.extend(self._interactions.values())
            all_entities.extend(self._deals.values())
            all_entities.extend(self._users.values())
            
            result = all_entities[offset:offset + limit]
            return result
            
        except Exception as e:
            self._handle_error("get_all_crm_entities", e)
    
    async def update(self, entity_id: UUID, update_data: Dict[str, Any]) -> Optional[Union[Contact, Company, Interaction, Deal, User]]:
        """エンティティを更新（汎用メソッド）"""
        # 実装の簡略化のため、具体的なタイプ別メソッドを使用することを推奨
        pass
    
    async def delete(self, entity_id: UUID) -> bool:
        """エンティティを削除（汎用メソッド）"""
        # 実装の簡略化のため、具体的なタイプ別メソッドを使用することを推奨
        pass
    
    async def exists(self, entity_id: UUID) -> bool:
        """エンティティの存在確認（汎用メソッド）"""
        entity = await self.get_by_id(entity_id)
        return entity is not None
    
    # 連絡先関連メソッド
    async def get_contact_by_id(self, contact_id: int) -> Optional[Contact]:
        """連絡先をIDで取得"""
        return self._contacts.get(contact_id)
    
    async def get_contacts_by_company(self, company_id: int) -> List[Contact]:
        """会社IDで連絡先を取得"""
        return [contact for contact in self._contacts.values() if contact.CompanyID == company_id]
    
    # 会社関連メソッド
    async def get_company_by_id(self, company_id: int) -> Optional[Company]:
        """会社をIDで取得"""
        return self._companies.get(company_id)
    
    async def search_companies_by_name(self, name: str) -> List[Company]:
        """名前で会社を検索"""
        return [company for company in self._companies.values() 
                if company.CompanyName and name.lower() in company.CompanyName.lower()]
    
    # 商談関連メソッド
    async def get_deal_by_id(self, deal_id: int) -> Optional[Deal]:
        """商談をIDで取得"""
        return self._deals.get(deal_id)
    
    async def get_deals_by_stage(self, stage: str) -> List[Deal]:
        """ステージで商談を取得"""
        return [deal for deal in self._deals.values() if deal.Stage == stage]
    
    # インタラクション関連メソッド
    async def get_interaction_by_id(self, interaction_id: int) -> Optional[Interaction]:
        """インタラクションをIDで取得"""
        return self._interactions.get(interaction_id)
    
    async def get_interactions_by_contact(self, contact_id: int) -> List[Interaction]:
        """連絡先でインタラクションを取得"""
        return [interaction for interaction in self._interactions.values() 
                if interaction.ContactID == contact_id]
    
    # ユーザー関連メソッド
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ユーザーをIDで取得"""
        return self._users.get(user_id)