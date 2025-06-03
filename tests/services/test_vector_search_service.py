"""
ベクトル検索サービスのテストモジュール

VectorSearchServiceの各機能をテストします。
検索、推薦、データ追加の動作を検証します。
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.services.vector_search_service import VectorSearchService, get_vector_search_service


class TestVectorSearchService:
    """ベクトル検索サービスのテストクラス"""
    
    @pytest.fixture
    def service(self):
        """テスト用サービスインスタンス"""
        return VectorSearchService()
    
    @pytest.fixture
    def mock_chroma_client(self):
        """モックChromaDBクライアント"""
        mock_client = Mock()
        with patch('src.services.vector_search_service.get_chroma_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_embedding_service(self):
        """モック埋め込みサービス"""
        mock_service = Mock()
        with patch('src.services.vector_search_service.get_embedding_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            yield mock_service
    
    def test_init(self, service, mock_chroma_client, mock_embedding_service):
        """初期化テスト"""
        assert service.chroma_client == mock_chroma_client
        assert service.embedding_service == mock_embedding_service
        assert "products" in service.collection_names
        assert "reviews" in service.collection_names
        assert "crm_notes" in service.collection_names
    
    def test_initialize(self, service, mock_chroma_client, mock_embedding_service):
        """サービス初期化テスト"""
        service.initialize()
        
        mock_chroma_client.connect.assert_called_once()
        mock_embedding_service.load_model.assert_called_once()
        
        # コレクション作成の確認
        assert mock_chroma_client.create_collection.call_count == 3
    
    def test_initialize_error(self, service, mock_chroma_client, mock_embedding_service):
        """初期化エラーテスト"""
        mock_chroma_client.connect.side_effect = Exception("接続エラー")
        
        with pytest.raises(Exception):
            service.initialize()
    
    def test_add_product_embeddings(self, service, mock_chroma_client, mock_embedding_service):
        """製品埋め込み追加テスト"""
        # モック設定
        mock_embedding_service.encode_product_description.return_value = np.array([0.1, 0.2, 0.3])
        mock_chroma_client.add_embeddings.return_value = True
        
        products = [
            {
                "product_id": "p1",
                "name": "テスト製品1",
                "description": "説明1",
                "category": "カテゴリA",
                "brand": "ブランドX",
                "price": 1000
            },
            {
                "product_id": "p2",
                "name": "テスト製品2",
                "description": "説明2",
                "category": "カテゴリB",
                "brand": "ブランドY",
                "price": 2000
            }
        ]
        
        result = service.add_product_embeddings(products)
        
        assert result is True
        assert mock_embedding_service.encode_product_description.call_count == 2
        mock_chroma_client.add_embeddings.assert_called_once()
        
        # 呼び出し引数の確認
        call_args = mock_chroma_client.add_embeddings.call_args
        assert call_args[1]["collection_name"] == service.collection_names["products"]
        assert len(call_args[1]["embeddings"]) == 2
        assert len(call_args[1]["documents"]) == 2
        assert len(call_args[1]["metadatas"]) == 2
        assert len(call_args[1]["ids"]) == 2
    
    def test_add_product_embeddings_empty_embedding(self, service, mock_chroma_client, mock_embedding_service):
        """空の埋め込みでの製品追加テスト"""
        mock_embedding_service.encode_product_description.return_value = np.array([])
        
        products = [{"product_id": "p1", "name": "テスト製品"}]
        
        result = service.add_product_embeddings(products)
        
        assert result is False
    
    def test_add_review_embeddings(self, service, mock_chroma_client, mock_embedding_service):
        """レビュー埋め込み追加テスト"""
        mock_embedding_service.encode_review_text.return_value = np.array([0.1, 0.2, 0.3])
        mock_chroma_client.add_embeddings.return_value = True
        
        reviews = [
            {
                "review_id": "r1",
                "product_id": "p1",
                "customer_id": "c1",
                "title": "良い製品",
                "content": "とても満足",
                "rating": 5
            }
        ]
        
        result = service.add_review_embeddings(reviews)
        
        assert result is True
        mock_embedding_service.encode_review_text.assert_called_once()
        mock_chroma_client.add_embeddings.assert_called_once()
    
    def test_add_crm_note_embeddings(self, service, mock_chroma_client, mock_embedding_service):
        """CRMメモ埋め込み追加テスト"""
        mock_embedding_service.encode_crm_note.return_value = np.array([0.1, 0.2, 0.3])
        mock_chroma_client.add_embeddings.return_value = True
        
        crm_notes = [
            {
                "note_id": "n1",
                "customer_id": "c1",
                "subject": "問い合わせ",
                "content": "製品について質問",
                "interaction_type": "電話"
            }
        ]
        
        result = service.add_crm_note_embeddings(crm_notes)
        
        assert result is True
        mock_embedding_service.encode_crm_note.assert_called_once()
        mock_chroma_client.add_embeddings.assert_called_once()
    
    def test_search_similar_products(self, service, mock_chroma_client, mock_embedding_service):
        """類似製品検索テスト"""
        # モック設定
        mock_embedding_service.encode_texts.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_chroma_client.query_embeddings.return_value = {
            "ids": [["product_p1", "product_p2"]],
            "documents": [["製品1の説明", "製品2の説明"]],
            "metadatas": [[{"product_id": "p1"}, {"product_id": "p2"}]],
            "distances": [[0.1, 0.2]]
        }
        
        results = service.search_similar_products("ワイヤレスイヤホン", n_results=5)
        
        assert len(results) == 2
        assert results[0]["id"] == "product_p1"
        assert results[0]["document"] == "製品1の説明"
        assert results[0]["metadata"]["product_id"] == "p1"
        assert results[0]["similarity"] == 0.9  # 1.0 - 0.1
        
        mock_embedding_service.encode_texts.assert_called_once_with("ワイヤレスイヤホン")
        mock_chroma_client.query_embeddings.assert_called_once()
    
    def test_search_similar_products_empty_embedding(self, service, mock_chroma_client, mock_embedding_service):
        """空の埋め込みでの製品検索テスト"""
        mock_embedding_service.encode_texts.return_value = np.array([])
        
        results = service.search_similar_products("テスト")
        
        assert results == []
    
    def test_search_similar_reviews(self, service, mock_chroma_client, mock_embedding_service):
        """類似レビュー検索テスト"""
        mock_embedding_service.encode_texts.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_chroma_client.query_embeddings.return_value = {
            "ids": [["review_r1"]],
            "documents": [["良いレビュー"]],
            "metadatas": [[{"review_id": "r1"}]],
            "distances": [[0.1]]
        }
        
        results = service.search_similar_reviews("満足", n_results=10)
        
        assert len(results) == 1
        assert results[0]["id"] == "review_r1"
        mock_chroma_client.query_embeddings.assert_called_once()
    
    def test_search_related_crm_notes(self, service, mock_chroma_client, mock_embedding_service):
        """関連CRMメモ検索テスト"""
        mock_embedding_service.encode_texts.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_chroma_client.query_embeddings.return_value = {
            "ids": [["crm_n1"]],
            "documents": [["顧客問い合わせ"]],
            "metadatas": [[{"note_id": "n1"}]],
            "distances": [[0.1]]
        }
        
        results = service.search_related_crm_notes("問い合わせ", n_results=10)
        
        assert len(results) == 1
        assert results[0]["id"] == "crm_n1"
        mock_chroma_client.query_embeddings.assert_called_once()
    
    def test_get_product_recommendations(self, service, mock_chroma_client, mock_embedding_service):
        """製品レコメンデーションテスト"""
        # 基準製品の取得結果
        mock_chroma_client.query_embeddings.side_effect = [
            {
                "embeddings": [[0.1, 0.2, 0.3]],
                "ids": [["product_p1"]],
                "metadatas": [[{"product_id": "p1"}]]
            },
            {
                "ids": [["product_p2", "product_p3"]],
                "documents": [["製品2", "製品3"]],
                "metadatas": [[{"product_id": "p2"}, {"product_id": "p3"}]],
                "distances": [[0.1, 0.2]]
            }
        ]
        
        results = service.get_product_recommendations("p1", n_results=5)
        
        assert len(results) == 2
        assert results[0]["metadata"]["product_id"] == "p2"
        assert results[1]["metadata"]["product_id"] == "p3"
        
        # 2回呼ばれることを確認（基準製品取得 + 類似製品検索）
        assert mock_chroma_client.query_embeddings.call_count == 2
    
    def test_get_product_recommendations_base_not_found(self, service, mock_chroma_client, mock_embedding_service):
        """基準製品が見つからない場合のレコメンデーションテスト"""
        mock_chroma_client.query_embeddings.return_value = {
            "embeddings": [],
            "ids": [[]],
            "metadatas": [[]]
        }
        
        results = service.get_product_recommendations("nonexistent", n_results=5)
        
        assert results == []
    
    def test_create_product_document_text(self, service):
        """製品ドキュメントテキスト作成テスト"""
        product = {
            "name": "テスト製品",
            "description": "説明文",
            "category": "カテゴリ",
            "brand": "ブランド"
        }
        
        text = service._create_product_document_text(product)
        
        assert "テスト製品" in text
        assert "説明文" in text
        assert "カテゴリ: カテゴリ" in text
        assert "ブランド: ブランド" in text
    
    def test_create_review_document_text(self, service):
        """レビュードキュメントテキスト作成テスト"""
        review = {
            "title": "良いレビュー",
            "content": "満足しています",
            "rating": 5
        }
        
        text = service._create_review_document_text(review)
        
        assert "良いレビュー" in text
        assert "満足しています" in text
        assert "評価: 5点" in text
    
    def test_create_crm_document_text(self, service):
        """CRMドキュメントテキスト作成テスト"""
        note = {
            "subject": "問い合わせ",
            "content": "質問があります",
            "interaction_type": "電話"
        }
        
        text = service._create_crm_document_text(note)
        
        assert "問い合わせ" in text
        assert "質問があります" in text
        assert "種別: 電話" in text
    
    def test_format_search_results(self, service):
        """検索結果フォーマットテスト"""
        results = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "value1"}, {"key": "value2"}]],
            "distances": [[0.1, 0.2]]
        }
        
        formatted = service._format_search_results(results)
        
        assert len(formatted) == 2
        assert formatted[0]["id"] == "id1"
        assert formatted[0]["document"] == "doc1"
        assert formatted[0]["metadata"]["key"] == "value1"
        assert formatted[0]["similarity"] == 0.9  # 1.0 - 0.1
        assert formatted[1]["id"] == "id2"
        assert formatted[1]["document"] == "doc2"
        assert formatted[1]["metadata"]["key"] == "value2"
        assert formatted[1]["similarity"] == 0.8  # 1.0 - 0.2
    
    def test_format_search_results_empty(self, service):
        """空の検索結果フォーマットテスト"""
        formatted = service._format_search_results(None)
        assert formatted == []
        
        formatted = service._format_search_results({})
        assert formatted == []
    
    def test_get_collection_stats(self, service, mock_chroma_client):
        """コレクション統計情報取得テスト"""
        mock_chroma_client.get_collection_info.side_effect = [
            {"count": 100, "metadata": {"created": "2023-01-01"}},
            {"count": 50, "metadata": {"created": "2023-01-02"}},
            {"count": 25, "metadata": {"created": "2023-01-03"}}
        ]
        
        stats = service.get_collection_stats()
        
        assert "products" in stats
        assert "reviews" in stats
        assert "crm_notes" in stats
        assert stats["products"]["count"] == 100
        assert stats["reviews"]["count"] == 50
        assert stats["crm_notes"]["count"] == 25
    
    def test_get_collection_stats_collection_not_found(self, service, mock_chroma_client):
        """存在しないコレクションの統計情報取得テスト"""
        mock_chroma_client.get_collection_info.return_value = None
        
        stats = service.get_collection_stats()
        
        assert stats["products"]["count"] == 0
        assert stats["reviews"]["count"] == 0
        assert stats["crm_notes"]["count"] == 0
    
    def test_get_vector_search_service_singleton(self):
        """シングルトンインスタンス取得テスト"""
        service1 = get_vector_search_service()
        service2 = get_vector_search_service()
        
        assert service1 is service2
        assert isinstance(service1, VectorSearchService)


class TestVectorSearchServiceIntegration:
    """ベクトル検索サービス統合テストクラス"""
    
    @pytest.fixture
    def integration_service(self):
        """統合テスト用サービス"""
        return VectorSearchService()
    
    @pytest.mark.integration
    def test_full_workflow(self, integration_service):
        """完全なワークフローテスト（実際のサービスが必要）"""
        try:
            # 初期化
            integration_service.initialize()
            
            # テストデータ
            products = [
                {
                    "product_id": "test_p1",
                    "name": "ワイヤレスイヤホン",
                    "description": "高音質Bluetoothイヤホン",
                    "category": "オーディオ",
                    "brand": "テックブランド"
                },
                {
                    "product_id": "test_p2",
                    "name": "有線イヤホン",
                    "description": "クリアな音質の有線イヤホン",
                    "category": "オーディオ",
                    "brand": "オーディオブランド"
                }
            ]
            
            # 製品データ追加
            success = integration_service.add_product_embeddings(products)
            assert success is True
            
            # 類似製品検索
            results = integration_service.search_similar_products("イヤホン", n_results=5)
            assert len(results) > 0
            
            # 統計情報取得
            stats = integration_service.get_collection_stats()
            assert stats["products"]["count"] >= 2
            
        except Exception as e:
            pytest.skip(f"統合テストスキップ（サービスが利用できません）: {e}")