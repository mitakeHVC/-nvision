"""
ベースリポジトリクラス

全てのリポジトリクラスの基底クラス
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    ベースリポジトリクラス
    
    全てのリポジトリクラスが継承する抽象基底クラス
    共通のCRUD操作を定義
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        エンティティを作成
        
        Args:
            entity: 作成するエンティティ
            
        Returns:
            作成されたエンティティ
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        IDでエンティティを取得
        
        Args:
            entity_id: エンティティID
            
        Returns:
            エンティティまたはNone
        """
        pass
    
    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        全てのエンティティを取得
        
        Args:
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            エンティティのリスト
        """
        pass
    
    @abstractmethod
    async def update(self, entity_id: UUID, update_data: Dict[str, Any]) -> Optional[T]:
        """
        エンティティを更新
        
        Args:
            entity_id: エンティティID
            update_data: 更新データ
            
        Returns:
            更新されたエンティティまたはNone
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """
        エンティティを削除
        
        Args:
            entity_id: エンティティID
            
        Returns:
            削除成功の場合True
        """
        pass
    
    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """
        エンティティの存在確認
        
        Args:
            entity_id: エンティティID
            
        Returns:
            存在する場合True
        """
        pass
    
    async def count(self) -> int:
        """
        エンティティの総数を取得
        
        Returns:
            エンティティの総数
        """
        entities = await self.get_all()
        return len(entities)
    
    def _log_operation(self, operation: str, entity_id: Optional[UUID] = None, **kwargs):
        """
        操作をログに記録
        
        Args:
            operation: 操作名
            entity_id: エンティティID
            **kwargs: 追加のログ情報
        """
        log_data = {"operation": operation}
        if entity_id:
            log_data["entity_id"] = str(entity_id)
        log_data.update(kwargs)
        
        self.logger.info(f"Repository operation: {operation}", extra=log_data)
    
    def _handle_error(self, operation: str, error: Exception, entity_id: Optional[UUID] = None):
        """
        エラーハンドリング
        
        Args:
            operation: 操作名
            error: 発生したエラー
            entity_id: エンティティID
        """
        log_data = {"operation": operation, "error": str(error)}
        if entity_id:
            log_data["entity_id"] = str(entity_id)
        
        self.logger.error(f"Repository error in {operation}: {error}", extra=log_data)
        raise error


class RepositoryError(Exception):
    """リポジトリ操作エラー"""
    pass


class EntityNotFoundError(RepositoryError):
    """エンティティが見つからないエラー"""
    pass


class DuplicateEntityError(RepositoryError):
    """重複エンティティエラー"""
    pass


class DatabaseConnectionError(RepositoryError):
    """データベース接続エラー"""
    pass