"""
ベクトル検索サービスモジュール

ChromaDBを使用したベクトル類似度検索とセマンティック検索機能を提供します。
製品、レビュー、CRMデータの関連性検索や推薦機能を実装します。
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
from datetime import datetime

from ..database.chroma_client import get_chroma_client
from ..services.embedding_service import get_embedding_service
from ..config.database_config import get_collection_names

logger = logging.getLogger(__name__)


class VectorSearchService:
    """ベクトル検索サービスクラス"""
    
    def __init__(self):
        """ベクトル検索サービスを初期化"""
        self.chroma_client = get_chroma_client()
        self.embedding_service = get_embedding_service()
        self.collection_names = get_collection_names()
        
    def initialize(self) -> None:
        """サービスを初期化（データベース接続とモデルロード）"""
        try:
            # ChromaDB接続
            self.chroma_client.connect()
            
            # 埋め込みモデルロード
            self.embedding_service.load_model()
            
            # 必要なコレクションを作成
            self._ensure_collections()
            
            logger.info("ベクトル検索サービス初期化完了")
            
        except Exception as e:
            logger.error(f"ベクトル検索サービス初期化エラー: {e}")
            raise
    
    def _ensure_collections(self) -> None:
        """必要なコレクションが存在することを確認"""
        for collection_name in self.collection_names.values():
            self.chroma_client.create_collection(
                collection_name,
                metadata={"created_at": datetime.now().isoformat()}
            )
    
    def add_product_embeddings(
        self,
        products: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> bool:
        """製品データの埋め込みを追加
        
        Args:
            products: 製品データのリスト
            batch_size: バッチサイズ
            
        Returns:
            bool: 追加成功の場合True
        """
        try:
            collection_name = self.collection_names["products"]
            
            embeddings = []
            documents = []
            metadatas = []
            ids = []
            
            for product in products:
                # 製品埋め込み生成
                embedding = self.embedding_service.encode_product_description(product)
                if embedding.size == 0:
                    continue
                    
                # ドキュメントテキスト作成
                doc_text = self._create_product_document_text(product)
                
                # メタデータ作成
                metadata = {
                    "product_id": product.get("product_id", ""),
                    "name": product.get("name", ""),
                    "category": product.get("category", ""),
                    "brand": product.get("brand", ""),
                    "price": product.get("price", 0),
                    "created_at": datetime.now().isoformat()
                }
                
                embeddings.append(embedding.tolist())
                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(f"product_{product.get('product_id', len(ids))}")
            
            if not embeddings:
                logger.warning("有効な製品埋め込みがありません")
                return False
                
            return self.chroma_client.add_embeddings(
                collection_name=collection_name,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            logger.error(f"製品埋め込み追加エラー: {e}")
            return False
    
    def add_review_embeddings(
        self,
        reviews: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> bool:
        """レビューデータの埋め込みを追加
        
        Args:
            reviews: レビューデータのリスト
            batch_size: バッチサイズ
            
        Returns:
            bool: 追加成功の場合True
        """
        try:
            collection_name = self.collection_names["reviews"]
            
            embeddings = []
            documents = []
            metadatas = []
            ids = []
            
            for review in reviews:
                # レビュー埋め込み生成
                embedding = self.embedding_service.encode_review_text(review)
                if embedding.size == 0:
                    continue
                    
                # ドキュメントテキスト作成
                doc_text = self._create_review_document_text(review)
                
                # メタデータ作成
                metadata = {
                    "review_id": review.get("review_id", ""),
                    "product_id": review.get("product_id", ""),
                    "customer_id": review.get("customer_id", ""),
                    "rating": review.get("rating", 0),
                    "sentiment": review.get("sentiment", ""),
                    "created_at": datetime.now().isoformat()
                }
                
                embeddings.append(embedding.tolist())
                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(f"review_{review.get('review_id', len(ids))}")
            
            if not embeddings:
                logger.warning("有効なレビュー埋め込みがありません")
                return False
                
            return self.chroma_client.add_embeddings(
                collection_name=collection_name,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            logger.error(f"レビュー埋め込み追加エラー: {e}")
            return False
    
    def add_crm_note_embeddings(
        self,
        crm_notes: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> bool:
        """CRMメモの埋め込みを追加
        
        Args:
            crm_notes: CRMメモデータのリスト
            batch_size: バッチサイズ
            
        Returns:
            bool: 追加成功の場合True
        """
        try:
            collection_name = self.collection_names["crm_notes"]
            
            embeddings = []
            documents = []
            metadatas = []
            ids = []
            
            for note in crm_notes:
                # CRMメモ埋め込み生成
                embedding = self.embedding_service.encode_crm_note(note)
                if embedding.size == 0:
                    continue
                    
                # ドキュメントテキスト作成
                doc_text = self._create_crm_document_text(note)
                
                # メタデータ作成
                metadata = {
                    "note_id": note.get("note_id", ""),
                    "customer_id": note.get("customer_id", ""),
                    "interaction_type": note.get("interaction_type", ""),
                    "priority": note.get("priority", ""),
                    "status": note.get("status", ""),
                    "created_at": datetime.now().isoformat()
                }
                
                embeddings.append(embedding.tolist())
                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(f"crm_{note.get('note_id', len(ids))}")
            
            if not embeddings:
                logger.warning("有効なCRMメモ埋め込みがありません")
                return False
                
            return self.chroma_client.add_embeddings(
                collection_name=collection_name,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            logger.error(f"CRMメモ埋め込み追加エラー: {e}")
            return False
    
    def search_similar_products(
        self,
        query_text: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """類似製品を検索
        
        Args:
            query_text: 検索クエリテキスト
            n_results: 取得する結果数
            filters: フィルタ条件
            
        Returns:
            List[Dict]: 検索結果のリスト
        """
        try:
            # クエリ埋め込み生成
            query_embedding = self.embedding_service.encode_texts(query_text)
            if query_embedding.size == 0:
                return []
                
            # 検索実行
            results = self.chroma_client.query_embeddings(
                collection_name=self.collection_names["products"],
                query_embeddings=[query_embedding[0].tolist()],
                n_results=n_results,
                where=filters
            )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"類似製品検索エラー: {e}")
            return []
    
    def search_similar_reviews(
        self,
        query_text: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """類似レビューを検索
        
        Args:
            query_text: 検索クエリテキスト
            n_results: 取得する結果数
            filters: フィルタ条件
            
        Returns:
            List[Dict]: 検索結果のリスト
        """
        try:
            # クエリ埋め込み生成
            query_embedding = self.embedding_service.encode_texts(query_text)
            if query_embedding.size == 0:
                return []
                
            # 検索実行
            results = self.chroma_client.query_embeddings(
                collection_name=self.collection_names["reviews"],
                query_embeddings=[query_embedding[0].tolist()],
                n_results=n_results,
                where=filters
            )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"類似レビュー検索エラー: {e}")
            return []
    
    def search_related_crm_notes(
        self,
        query_text: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """関連CRMメモを検索
        
        Args:
            query_text: 検索クエリテキスト
            n_results: 取得する結果数
            filters: フィルタ条件
            
        Returns:
            List[Dict]: 検索結果のリスト
        """
        try:
            # クエリ埋め込み生成
            query_embedding = self.embedding_service.encode_texts(query_text)
            if query_embedding.size == 0:
                return []
                
            # 検索実行
            results = self.chroma_client.query_embeddings(
                collection_name=self.collection_names["crm_notes"],
                query_embeddings=[query_embedding[0].tolist()],
                n_results=n_results,
                where=filters
            )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"関連CRMメモ検索エラー: {e}")
            return []
    
    def get_product_recommendations(
        self,
        product_id: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """製品レコメンデーション
        
        Args:
            product_id: 基準となる製品ID
            n_results: 推薦する製品数
            
        Returns:
            List[Dict]: 推薦製品のリスト
        """
        try:
            # 基準製品の情報を取得
            base_results = self.chroma_client.query_embeddings(
                collection_name=self.collection_names["products"],
                query_embeddings=[],  # 空のクエリで全件取得
                n_results=1000,  # 十分大きな数
                where={"product_id": product_id}
            )
            
            if not base_results or not base_results.get("embeddings"):
                logger.warning(f"基準製品が見つかりません: {product_id}")
                return []
                
            # 基準製品の埋め込みを使用して類似製品を検索
            base_embedding = base_results["embeddings"][0]
            
            results = self.chroma_client.query_embeddings(
                collection_name=self.collection_names["products"],
                query_embeddings=[base_embedding],
                n_results=n_results + 1,  # 自分自身を除くため+1
                where={"product_id": {"$ne": product_id}}  # 自分自身を除外
            )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"製品レコメンデーションエラー: {e}")
            return []
    
    def _create_product_document_text(self, product: Dict[str, Any]) -> str:
        """製品ドキュメントテキストを作成"""
        parts = []
        if product.get("name"):
            parts.append(product["name"])
        if product.get("description"):
            parts.append(product["description"])
        if product.get("category"):
            parts.append(f"カテゴリ: {product['category']}")
        if product.get("brand"):
            parts.append(f"ブランド: {product['brand']}")
        return " ".join(parts)
    
    def _create_review_document_text(self, review: Dict[str, Any]) -> str:
        """レビュードキュメントテキストを作成"""
        parts = []
        if review.get("title"):
            parts.append(review["title"])
        if review.get("content"):
            parts.append(review["content"])
        if review.get("rating"):
            parts.append(f"評価: {review['rating']}点")
        return " ".join(parts)
    
    def _create_crm_document_text(self, note: Dict[str, Any]) -> str:
        """CRMドキュメントテキストを作成"""
        parts = []
        if note.get("subject"):
            parts.append(note["subject"])
        if note.get("content"):
            parts.append(note["content"])
        if note.get("interaction_type"):
            parts.append(f"種別: {note['interaction_type']}")
        return " ".join(parts)
    
    def _format_search_results(self, results: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """検索結果をフォーマット"""
        if not results:
            return []
            
        formatted_results = []
        
        # 結果の各要素を処理
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        for i in range(len(ids)):
            result = {
                "id": ids[i],
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "similarity": 1.0 - distances[i] if i < len(distances) else 0.0  # 距離を類似度に変換
            }
            formatted_results.append(result)
            
        return formatted_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """コレクション統計情報を取得
        
        Returns:
            Dict: 統計情報
        """
        stats = {}
        
        for key, collection_name in self.collection_names.items():
            info = self.chroma_client.get_collection_info(collection_name)
            if info:
                stats[key] = {
                    "collection_name": collection_name,
                    "count": info.get("count", 0),
                    "metadata": info.get("metadata", {})
                }
            else:
                stats[key] = {
                    "collection_name": collection_name,
                    "count": 0,
                    "metadata": {}
                }
                
        return stats


# グローバルベクトル検索サービスインスタンス
vector_search_service = VectorSearchService()


def get_vector_search_service() -> VectorSearchService:
    """ベクトル検索サービスインスタンスを取得"""
    return vector_search_service