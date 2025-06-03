"""
ベクトル検索リポジトリ

ベクトル検索機能のCRUD操作を提供
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging
from datetime import datetime

from .base import BaseRepository, EntityNotFoundError
from ..database.chroma_client import get_chroma_client
from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorSearchResult:
    """ベクトル検索結果クラス"""
    
    def __init__(self, id: str, document: str, metadata: Dict[str, Any], distance: float):
        self.id = id
        self.document = document
        self.metadata = metadata
        self.distance = distance
        self.similarity = 1 - distance  # 類似度（距離の逆数）
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "document": self.document,
            "metadata": self.metadata,
            "distance": self.distance,
            "similarity": self.similarity
        }


class VectorRepository(BaseRepository[VectorSearchResult]):
    """
    ベクトル検索リポジトリ
    
    ベクトル埋め込みの保存、検索、更新、削除を提供
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        super().__init__()
        self.chroma_client = get_chroma_client()
        self.embedding_service = EmbeddingService()
        
        # デフォルトコレクション名
        self.collections = {
            "products": "product_embeddings",
            "customers": "customer_embeddings", 
            "orders": "order_embeddings",
            "reviews": "review_embeddings",
            "crm_contacts": "crm_contact_embeddings",
            "crm_companies": "crm_company_embeddings",
            "crm_interactions": "crm_interaction_embeddings"
        }
        
        # ChromaDBに接続
        self._ensure_connection()
        
        # サンプルデータの初期化
        self._initialize_sample_data()
    
    def _ensure_connection(self):
        """ChromaDB接続を確保"""
        try:
            if not self.chroma_client.client:
                self.chroma_client.connect()
            self.logger.info("ChromaDB connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def _initialize_sample_data(self):
        """サンプルデータの初期化"""
        try:
            # 製品データのサンプル埋め込み
            product_documents = [
                "高性能なビジネス向けノートパソコン 軽量 長時間バッテリー",
                "エルゴノミクスデザインのワイヤレスマウス 快適操作",
                "プログラマー向け高品質メカニカルキーボード RGB バックライト"
            ]
            
            product_metadatas = [
                {"type": "product", "product_id": 1, "category": "ノートパソコン", "price": 120000},
                {"type": "product", "product_id": 2, "category": "マウス", "price": 3500},
                {"type": "product", "product_id": 3, "category": "キーボード", "price": 15000}
            ]
            
            # 顧客レビューのサンプル埋め込み
            review_documents = [
                "とても満足しています。性能が良く、デザインも気に入っています。",
                "価格に対して品質が高く、コストパフォーマンスが優秀です。",
                "使いやすく、長時間使用しても疲れません。おすすめです。"
            ]
            
            review_metadatas = [
                {"type": "review", "review_id": 1, "product_id": 1, "rating": 5, "sentiment": "positive"},
                {"type": "review", "review_id": 2, "product_id": 2, "rating": 4, "sentiment": "positive"},
                {"type": "review", "review_id": 3, "product_id": 3, "rating": 5, "sentiment": "positive"}
            ]
            
            # 埋め込みを生成して保存
            self._add_sample_embeddings("products", product_documents, product_metadatas)
            self._add_sample_embeddings("reviews", review_documents, review_metadatas)
            
            self.logger.info("Sample vector data initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sample data: {e}")
    
    def _add_sample_embeddings(self, collection_type: str, documents: List[str], metadatas: List[Dict[str, Any]]):
        """サンプル埋め込みを追加"""
        try:
            collection_name = self.collections.get(collection_type)
            if not collection_name:
                return
            
            # 埋め込みを生成
            embeddings = []
            for doc in documents:
                embedding = self.embedding_service.generate_embedding(doc)
                embeddings.append(embedding)
            
            # IDを生成
            ids = [f"{collection_type}_{i+1}" for i in range(len(documents))]
            
            # ChromaDBに追加
            success = self.chroma_client.add_embeddings(
                collection_name=collection_name,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            if success:
                self.logger.info(f"Added {len(documents)} sample embeddings to {collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to add sample embeddings for {collection_type}: {e}")
    
    async def create(self, entity: VectorSearchResult) -> VectorSearchResult:
        """ベクトル埋め込みを作成"""
        # このメソッドは直接的には使用されない
        # add_document メソッドを使用することを推奨
        raise NotImplementedError("Use add_document method instead")
    
    async def get_by_id(self, entity_id: UUID) -> Optional[VectorSearchResult]:
        """IDでベクトルデータを取得"""
        # 実装の簡略化のため、search_by_id メソッドを使用することを推奨
        raise NotImplementedError("Use search_by_id method instead")
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[VectorSearchResult]:
        """全てのベクトルデータを取得"""
        # 実装の簡略化のため、list_documents メソッドを使用することを推奨
        raise NotImplementedError("Use list_documents method instead")
    
    async def update(self, entity_id: UUID, update_data: Dict[str, Any]) -> Optional[VectorSearchResult]:
        """ベクトルデータを更新"""
        # update_document メソッドを使用することを推奨
        raise NotImplementedError("Use update_document method instead")
    
    async def delete(self, entity_id: UUID) -> bool:
        """ベクトルデータを削除"""
        # delete_document メソッドを使用することを推奨
        raise NotImplementedError("Use delete_document method instead")
    
    async def exists(self, entity_id: UUID) -> bool:
        """ベクトルデータの存在確認"""
        # 実装の簡略化のため、具体的な検索メソッドを使用することを推奨
        return False
    
    async def add_document(
        self,
        collection_type: str,
        document: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> bool:
        """ドキュメントを追加"""
        try:
            self._log_operation("add_document", collection_type=collection_type)
            
            collection_name = self.collections.get(collection_type)
            if not collection_name:
                raise ValueError(f"Unknown collection type: {collection_type}")
            
            # 埋め込みを生成
            embedding = self.embedding_service.generate_embedding(document)
            
            # IDを生成（指定されていない場合）
            if not document_id:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                document_id = f"{collection_type}_{timestamp}"
            
            # ChromaDBに追加
            success = self.chroma_client.add_embeddings(
                collection_name=collection_name,
                embeddings=[embedding],
                documents=[document],
                metadatas=[metadata],
                ids=[document_id]
            )
            
            if success:
                self.logger.info(f"Document added successfully: {document_id}")
            
            return success
            
        except Exception as e:
            self._handle_error("add_document", e)
            return False
    
    async def search_similar(
        self,
        collection_type: str,
        query_text: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """類似ドキュメントを検索"""
        try:
            self._log_operation("search_similar", collection_type=collection_type, query=query_text)
            
            collection_name = self.collections.get(collection_type)
            if not collection_name:
                raise ValueError(f"Unknown collection type: {collection_type}")
            
            # クエリの埋め込みを生成
            query_embedding = self.embedding_service.generate_embedding(query_text)
            
            # ChromaDBで検索
            results = self.chroma_client.query_embeddings(
                collection_name=collection_name,
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            
            if not results:
                return []
            
            # 結果を変換
            search_results = []
            for i in range(len(results['ids'][0])):
                result = VectorSearchResult(
                    id=results['ids'][0][i],
                    document=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    distance=results['distances'][0][i]
                )
                search_results.append(result)
            
            self.logger.info(f"Found {len(search_results)} similar documents")
            return search_results
            
        except Exception as e:
            self._handle_error("search_similar", e)
            return []
    
    async def update_document(
        self,
        collection_type: str,
        document_id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """ドキュメントを更新"""
        try:
            self._log_operation("update_document", collection_type=collection_type, document_id=document_id)
            
            collection_name = self.collections.get(collection_type)
            if not collection_name:
                raise ValueError(f"Unknown collection type: {collection_type}")
            
            # 新しい埋め込みを生成（ドキュメントが更新される場合）
            embedding = None
            if document:
                embedding = self.embedding_service.generate_embedding(document)
            
            # ChromaDBで更新
            success = self.chroma_client.update_embeddings(
                collection_name=collection_name,
                ids=[document_id],
                embeddings=[embedding] if embedding else None,
                documents=[document] if document else None,
                metadatas=[metadata] if metadata else None
            )
            
            if success:
                self.logger.info(f"Document updated successfully: {document_id}")
            
            return success
            
        except Exception as e:
            self._handle_error("update_document", e)
            return False
    
    async def delete_document(self, collection_type: str, document_id: str) -> bool:
        """ドキュメントを削除"""
        try:
            self._log_operation("delete_document", collection_type=collection_type, document_id=document_id)
            
            collection_name = self.collections.get(collection_type)
            if not collection_name:
                raise ValueError(f"Unknown collection type: {collection_type}")
            
            # ChromaDBから削除
            success = self.chroma_client.delete_embeddings(
                collection_name=collection_name,
                ids=[document_id]
            )
            
            if success:
                self.logger.info(f"Document deleted successfully: {document_id}")
            
            return success
            
        except Exception as e:
            self._handle_error("delete_document", e)
            return False