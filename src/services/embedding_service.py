"""
埋め込みサービスモジュール

Sentence Transformersを使用してテキストのベクトル埋め込みを生成します。
製品説明、レビュー、CRMメモなどの様々なテキストデータを処理し、
セマンティック検索に適したベクトル表現を作成します。
"""

import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from ..config.database_config import get_embedding_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """テキスト埋め込みサービスクラス"""
    
    def __init__(self, model_name: Optional[str] = None):
        """埋め込みサービスを初期化
        
        Args:
            model_name: 使用するSentence Transformersモデル名
        """
        self.config = get_embedding_config()
        self.model_name = model_name or self.config["model_name"]
        self.dimension = self.config["dimension"]
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    def load_model(self) -> None:
        """埋め込みモデルをロード"""
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"埋め込みモデルロード成功: {self.model_name} (device: {self.device})")
        except Exception as e:
            logger.error(f"埋め込みモデルロードエラー: {self.model_name}, {e}")
            raise
    
    def encode_texts(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """テキストを埋め込みベクトルに変換
        
        Args:
            texts: 埋め込み対象のテキスト（単一または複数）
            batch_size: バッチサイズ
            normalize_embeddings: 埋め込みベクトルを正規化するか
            show_progress_bar: プログレスバーを表示するか
            
        Returns:
            np.ndarray: 埋め込みベクトル配列
        """
        if not self.model:
            self.load_model()
            
        try:
            # 単一テキストの場合はリストに変換
            if isinstance(texts, str):
                texts = [texts]
                
            # 空のテキストを除外
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                logger.warning("有効なテキストがありません")
                return np.array([])
                
            # 埋め込み生成
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                normalize_embeddings=normalize_embeddings,
                show_progress_bar=show_progress_bar,
                convert_to_numpy=True
            )
            
            logger.info(f"埋め込み生成成功: {len(valid_texts)}件, 次元数: {embeddings.shape[1]}")
            return embeddings
            
        except Exception as e:
            logger.error(f"埋め込み生成エラー: {e}")
            raise
    
    def encode_product_description(self, product_data: Dict[str, Any]) -> np.ndarray:
        """製品データから埋め込みベクトルを生成
        
        Args:
            product_data: 製品データ辞書
            
        Returns:
            np.ndarray: 製品の埋め込みベクトル
        """
        try:
            # 製品情報を結合してテキスト化
            text_parts = []
            
            if product_data.get("name"):
                text_parts.append(f"製品名: {product_data['name']}")
                
            if product_data.get("description"):
                text_parts.append(f"説明: {product_data['description']}")
                
            if product_data.get("category"):
                text_parts.append(f"カテゴリ: {product_data['category']}")
                
            if product_data.get("brand"):
                text_parts.append(f"ブランド: {product_data['brand']}")
                
            if product_data.get("tags"):
                tags = product_data["tags"]
                if isinstance(tags, list):
                    text_parts.append(f"タグ: {', '.join(tags)}")
                else:
                    text_parts.append(f"タグ: {tags}")
            
            combined_text = " ".join(text_parts)
            
            if not combined_text.strip():
                logger.warning("製品データからテキストを抽出できませんでした")
                return np.array([])
                
            return self.encode_texts(combined_text)[0]
            
        except Exception as e:
            logger.error(f"製品埋め込み生成エラー: {e}")
            raise
    
    def encode_review_text(self, review_data: Dict[str, Any]) -> np.ndarray:
        """レビューデータから埋め込みベクトルを生成
        
        Args:
            review_data: レビューデータ辞書
            
        Returns:
            np.ndarray: レビューの埋め込みベクトル
        """
        try:
            text_parts = []
            
            if review_data.get("title"):
                text_parts.append(f"タイトル: {review_data['title']}")
                
            if review_data.get("content"):
                text_parts.append(f"内容: {review_data['content']}")
                
            if review_data.get("rating"):
                text_parts.append(f"評価: {review_data['rating']}点")
            
            combined_text = " ".join(text_parts)
            
            if not combined_text.strip():
                logger.warning("レビューデータからテキストを抽出できませんでした")
                return np.array([])
                
            return self.encode_texts(combined_text)[0]
            
        except Exception as e:
            logger.error(f"レビュー埋め込み生成エラー: {e}")
            raise
    
    def encode_crm_note(self, crm_data: Dict[str, Any]) -> np.ndarray:
        """CRMメモから埋め込みベクトルを生成
        
        Args:
            crm_data: CRMデータ辞書
            
        Returns:
            np.ndarray: CRMメモの埋め込みベクトル
        """
        try:
            text_parts = []
            
            if crm_data.get("subject"):
                text_parts.append(f"件名: {crm_data['subject']}")
                
            if crm_data.get("content"):
                text_parts.append(f"内容: {crm_data['content']}")
                
            if crm_data.get("interaction_type"):
                text_parts.append(f"種別: {crm_data['interaction_type']}")
                
            if crm_data.get("tags"):
                tags = crm_data["tags"]
                if isinstance(tags, list):
                    text_parts.append(f"タグ: {', '.join(tags)}")
                else:
                    text_parts.append(f"タグ: {tags}")
            
            combined_text = " ".join(text_parts)
            
            if not combined_text.strip():
                logger.warning("CRMデータからテキストを抽出できませんでした")
                return np.array([])
                
            return self.encode_texts(combined_text)[0]
            
        except Exception as e:
            logger.error(f"CRM埋め込み生成エラー: {e}")
            raise
    
    def calculate_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        method: str = "cosine"
    ) -> float:
        """2つの埋め込みベクトル間の類似度を計算
        
        Args:
            embedding1: 埋め込みベクトル1
            embedding2: 埋め込みベクトル2
            method: 類似度計算方法（"cosine", "euclidean", "dot"）
            
        Returns:
            float: 類似度スコア
        """
        try:
            if method == "cosine":
                # コサイン類似度
                dot_product = np.dot(embedding1, embedding2)
                norm1 = np.linalg.norm(embedding1)
                norm2 = np.linalg.norm(embedding2)
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                    
                return dot_product / (norm1 * norm2)
                
            elif method == "euclidean":
                # ユークリッド距離（類似度に変換）
                distance = np.linalg.norm(embedding1 - embedding2)
                return 1.0 / (1.0 + distance)
                
            elif method == "dot":
                # 内積
                return np.dot(embedding1, embedding2)
                
            else:
                raise ValueError(f"サポートされていない類似度計算方法: {method}")
                
        except Exception as e:
            logger.error(f"類似度計算エラー: {e}")
            return 0.0
    
    def batch_encode_with_metadata(
        self,
        data_list: List[Dict[str, Any]],
        text_field: str,
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """メタデータ付きでバッチ埋め込み生成
        
        Args:
            data_list: データリスト
            text_field: テキストフィールド名
            batch_size: バッチサイズ
            
        Returns:
            List[Dict]: 埋め込みとメタデータのリスト
        """
        try:
            # テキストを抽出
            texts = [item.get(text_field, "") for item in data_list]
            
            # 埋め込み生成
            embeddings = self.encode_texts(texts, batch_size=batch_size)
            
            # 結果を構築
            results = []
            for i, (item, embedding) in enumerate(zip(data_list, embeddings)):
                result = {
                    "embedding": embedding.tolist(),
                    "text": texts[i],
                    "metadata": {k: v for k, v in item.items() if k != text_field}
                }
                results.append(result)
                
            logger.info(f"バッチ埋め込み生成完了: {len(results)}件")
            return results
            
        except Exception as e:
            logger.error(f"バッチ埋め込み生成エラー: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得
        
        Returns:
            Dict: モデル情報
        """
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "device": self.device,
            "loaded": self.model is not None
        }


# グローバル埋め込みサービスインスタンス
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """埋め込みサービスインスタンスを取得"""
    return embedding_service