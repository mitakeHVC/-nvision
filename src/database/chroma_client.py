"""
ChromaDBクライアントモジュール

ChromaDBとの接続、コレクション管理、ベクトル操作を提供します。
ベクトル埋め込みの保存、検索、更新、削除などの基本的なCRUD操作を実装します。
"""

import logging
from typing import List, Dict, Any, Optional, Union
import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection
import numpy as np

from ..config.database_config import get_chroma_config, get_collection_names

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """ChromaDBクライアントクラス"""
    
    def __init__(self):
        """ChromaDBクライアントを初期化"""
        self.config = get_chroma_config()
        self.collection_names = get_collection_names()
        self.client = None
        self.collections: Dict[str, Collection] = {}
        
    def connect(self) -> None:
        """ChromaDBに接続"""
        try:
            # ChromaDBクライアントを初期化
            if self.config.get("persist_directory"):
                # ローカル永続化モード
                self.client = chromadb.PersistentClient(
                    path=self.config["persist_directory"]
                )
                logger.info(f"ChromaDB接続成功（永続化モード）: {self.config['persist_directory']}")
            else:
                # HTTPクライアントモード
                self.client = chromadb.HttpClient(
                    host=self.config["host"],
                    port=self.config["port"]
                )
                logger.info(f"ChromaDB接続成功（HTTPモード）: {self.config['host']}:{self.config['port']}")
                
        except Exception as e:
            logger.error(f"ChromaDB接続エラー: {e}")
            raise
    
    def disconnect(self) -> None:
        """ChromaDBから切断"""
        if self.client:
            self.client = None
            self.collections.clear()
            logger.info("ChromaDBから切断しました")
    
    def create_collection(self, collection_name: str, metadata: Optional[Dict[str, Any]] = None) -> Collection:
        """コレクションを作成または取得
        
        Args:
            collection_name: コレクション名
            metadata: コレクションのメタデータ
            
        Returns:
            Collection: 作成または取得されたコレクション
        """
        if not self.client:
            raise RuntimeError("ChromaDBに接続されていません")
            
        try:
            # 既存のコレクションを取得または新規作成
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=metadata or {}
            )
            self.collections[collection_name] = collection
            logger.info(f"コレクション作成/取得成功: {collection_name}")
            return collection
            
        except Exception as e:
            logger.error(f"コレクション作成エラー: {collection_name}, {e}")
            raise
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """コレクションを取得
        
        Args:
            collection_name: コレクション名
            
        Returns:
            Collection: 取得されたコレクション、存在しない場合はNone
        """
        if collection_name in self.collections:
            return self.collections[collection_name]
            
        if not self.client:
            raise RuntimeError("ChromaDBに接続されていません")
            
        try:
            collection = self.client.get_collection(name=collection_name)
            self.collections[collection_name] = collection
            return collection
        except Exception as e:
            logger.warning(f"コレクション取得失敗: {collection_name}, {e}")
            return None
    
    def delete_collection(self, collection_name: str) -> bool:
        """コレクションを削除
        
        Args:
            collection_name: コレクション名
            
        Returns:
            bool: 削除成功の場合True
        """
        if not self.client:
            raise RuntimeError("ChromaDBに接続されていません")
            
        try:
            self.client.delete_collection(name=collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]
            logger.info(f"コレクション削除成功: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"コレクション削除エラー: {collection_name}, {e}")
            return False
    
    def add_embeddings(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """埋め込みベクトルをコレクションに追加
        
        Args:
            collection_name: コレクション名
            embeddings: 埋め込みベクトルのリスト
            documents: ドキュメントテキストのリスト
            metadatas: メタデータのリスト
            ids: ドキュメントIDのリスト
            
        Returns:
            bool: 追加成功の場合True
        """
        collection = self.get_collection(collection_name)
        if not collection:
            collection = self.create_collection(collection_name)
            
        try:
            # IDが指定されていない場合は自動生成
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]
                
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"埋め込み追加成功: {collection_name}, {len(embeddings)}件")
            return True
            
        except Exception as e:
            logger.error(f"埋め込み追加エラー: {collection_name}, {e}")
            return False
    
    def query_embeddings(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """埋め込みベクトルで類似検索
        
        Args:
            collection_name: コレクション名
            query_embeddings: クエリ埋め込みベクトル
            n_results: 取得する結果数
            where: フィルタ条件
            include: 含める情報の種類
            
        Returns:
            Dict: 検索結果
        """
        collection = self.get_collection(collection_name)
        if not collection:
            logger.warning(f"コレクションが存在しません: {collection_name}")
            return None
            
        try:
            if include is None:
                include = ["documents", "metadatas", "distances"]
                
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                include=include
            )
            logger.info(f"検索実行成功: {collection_name}, {len(query_embeddings)}クエリ")
            return results
            
        except Exception as e:
            logger.error(f"検索エラー: {collection_name}, {e}")
            return None
    
    def update_embeddings(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """埋め込みベクトルを更新
        
        Args:
            collection_name: コレクション名
            ids: 更新するドキュメントIDのリスト
            embeddings: 新しい埋め込みベクトル
            documents: 新しいドキュメントテキスト
            metadatas: 新しいメタデータ
            
        Returns:
            bool: 更新成功の場合True
        """
        collection = self.get_collection(collection_name)
        if not collection:
            logger.warning(f"コレクションが存在しません: {collection_name}")
            return False
            
        try:
            collection.update(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"埋め込み更新成功: {collection_name}, {len(ids)}件")
            return True
            
        except Exception as e:
            logger.error(f"埋め込み更新エラー: {collection_name}, {e}")
            return False
    
    def delete_embeddings(self, collection_name: str, ids: List[str]) -> bool:
        """埋め込みベクトルを削除
        
        Args:
            collection_name: コレクション名
            ids: 削除するドキュメントIDのリスト
            
        Returns:
            bool: 削除成功の場合True
        """
        collection = self.get_collection(collection_name)
        if not collection:
            logger.warning(f"コレクションが存在しません: {collection_name}")
            return False
            
        try:
            collection.delete(ids=ids)
            logger.info(f"埋め込み削除成功: {collection_name}, {len(ids)}件")
            return True
            
        except Exception as e:
            logger.error(f"埋め込み削除エラー: {collection_name}, {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """コレクション情報を取得
        
        Args:
            collection_name: コレクション名
            
        Returns:
            Dict: コレクション情報
        """
        collection = self.get_collection(collection_name)
        if not collection:
            return None
            
        try:
            count = collection.count()
            return {
                "name": collection_name,
                "count": count,
                "metadata": collection.metadata
            }
        except Exception as e:
            logger.error(f"コレクション情報取得エラー: {collection_name}, {e}")
            return None
    
    def list_collections(self) -> List[str]:
        """全コレクション名を取得
        
        Returns:
            List[str]: コレクション名のリスト
        """
        if not self.client:
            raise RuntimeError("ChromaDBに接続されていません")
            
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"コレクション一覧取得エラー: {e}")
            return []


# グローバルクライアントインスタンス
chroma_client = ChromaDBClient()


def get_chroma_client() -> ChromaDBClient:
    """ChromaDBクライアントインスタンスを取得"""
    return chroma_client