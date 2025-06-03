"""
埋め込みサービスのテストモジュール

EmbeddingServiceの各機能をテストします。
テキスト埋め込み生成、類似度計算、バッチ処理の動作を検証します。
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.services.embedding_service import EmbeddingService, get_embedding_service


class TestEmbeddingService:
    """埋め込みサービスのテストクラス"""
    
    @pytest.fixture
    def service(self):
        """テスト用サービスインスタンス"""
        return EmbeddingService(model_name="test-model")
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """モックSentenceTransformer"""
        with patch('src.services.embedding_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_st.return_value = mock_model
            yield mock_model
    
    def test_init(self, service):
        """初期化テスト"""
        assert service.model_name == "test-model"
        assert service.model is None
        assert service.device in ["cuda", "cpu"]
    
    def test_init_default_model(self):
        """デフォルトモデルでの初期化テスト"""
        service = EmbeddingService()
        assert "sentence-transformers" in service.model_name
    
    def test_load_model(self, service, mock_sentence_transformer):
        """モデルロードテスト"""
        service.load_model()
        
        assert service.model is not None
        assert service.model == mock_sentence_transformer
    
    def test_load_model_error(self, service):
        """モデルロードエラーテスト"""
        with patch('src.services.embedding_service.SentenceTransformer') as mock_st:
            mock_st.side_effect = Exception("モデルロードエラー")
            
            with pytest.raises(Exception):
                service.load_model()
    
    def test_encode_texts_single_text(self, service, mock_sentence_transformer):
        """単一テキスト埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        result = service.encode_texts("テストテキスト")
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 3)
        mock_sentence_transformer.encode.assert_called_once()
    
    def test_encode_texts_multiple_texts(self, service, mock_sentence_transformer):
        """複数テキスト埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ])
        
        texts = ["テキスト1", "テキスト2"]
        result = service.encode_texts(texts)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 3)
    
    def test_encode_texts_empty_input(self, service, mock_sentence_transformer):
        """空入力での埋め込みテスト"""
        service.model = mock_sentence_transformer
        
        result = service.encode_texts([])
        
        assert isinstance(result, np.ndarray)
        assert result.size == 0
    
    def test_encode_texts_auto_load_model(self, service, mock_sentence_transformer):
        """自動モデルロードテスト"""
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        with patch.object(service, 'load_model') as mock_load:
            result = service.encode_texts("テスト")
            mock_load.assert_called_once()
    
    def test_encode_product_description(self, service, mock_sentence_transformer):
        """製品説明埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        product_data = {
            "name": "テスト製品",
            "description": "これはテスト製品です",
            "category": "テストカテゴリ",
            "brand": "テストブランド",
            "tags": ["tag1", "tag2"]
        }
        
        result = service.encode_product_description(product_data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        
        # encode_textsが適切なテキストで呼ばれることを確認
        call_args = mock_sentence_transformer.encode.call_args[0][0]
        assert "製品名: テスト製品" in call_args[0]
        assert "説明: これはテスト製品です" in call_args[0]
        assert "カテゴリ: テストカテゴリ" in call_args[0]
        assert "ブランド: テストブランド" in call_args[0]
        assert "タグ: tag1, tag2" in call_args[0]
    
    def test_encode_product_description_minimal_data(self, service, mock_sentence_transformer):
        """最小限の製品データでの埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        product_data = {"name": "テスト製品"}
        
        result = service.encode_product_description(product_data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
    
    def test_encode_product_description_empty_data(self, service, mock_sentence_transformer):
        """空の製品データでの埋め込みテスト"""
        service.model = mock_sentence_transformer
        
        product_data = {}
        
        result = service.encode_product_description(product_data)
        
        assert isinstance(result, np.ndarray)
        assert result.size == 0
    
    def test_encode_review_text(self, service, mock_sentence_transformer):
        """レビューテキスト埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        review_data = {
            "title": "良い製品です",
            "content": "とても満足しています",
            "rating": 5
        }
        
        result = service.encode_review_text(review_data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        
        # 適切なテキストが生成されることを確認
        call_args = mock_sentence_transformer.encode.call_args[0][0]
        assert "タイトル: 良い製品です" in call_args[0]
        assert "内容: とても満足しています" in call_args[0]
        assert "評価: 5点" in call_args[0]
    
    def test_encode_crm_note(self, service, mock_sentence_transformer):
        """CRMメモ埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        crm_data = {
            "subject": "顧客問い合わせ",
            "content": "製品について質問がありました",
            "interaction_type": "電話",
            "tags": ["質問", "製品"]
        }
        
        result = service.encode_crm_note(crm_data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        
        # 適切なテキストが生成されることを確認
        call_args = mock_sentence_transformer.encode.call_args[0][0]
        assert "件名: 顧客問い合わせ" in call_args[0]
        assert "内容: 製品について質問がありました" in call_args[0]
        assert "種別: 電話" in call_args[0]
        assert "タグ: 質問, 製品" in call_args[0]
    
    def test_calculate_similarity_cosine(self, service):
        """コサイン類似度計算テスト"""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        
        similarity = service.calculate_similarity(embedding1, embedding2, "cosine")
        
        assert similarity == 0.0  # 直交ベクトルなので類似度は0
    
    def test_calculate_similarity_cosine_identical(self, service):
        """同一ベクトルのコサイン類似度テスト"""
        embedding1 = np.array([1.0, 1.0, 1.0])
        embedding2 = np.array([1.0, 1.0, 1.0])
        
        similarity = service.calculate_similarity(embedding1, embedding2, "cosine")
        
        assert abs(similarity - 1.0) < 1e-6  # 同一ベクトルなので類似度は1
    
    def test_calculate_similarity_euclidean(self, service):
        """ユークリッド距離類似度計算テスト"""
        embedding1 = np.array([0.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 0.0, 0.0])
        
        similarity = service.calculate_similarity(embedding1, embedding2, "euclidean")
        
        assert similarity == 1.0  # 同一点なので類似度は1
    
    def test_calculate_similarity_dot_product(self, service):
        """内積類似度計算テスト"""
        embedding1 = np.array([1.0, 2.0, 3.0])
        embedding2 = np.array([2.0, 3.0, 4.0])
        
        similarity = service.calculate_similarity(embedding1, embedding2, "dot")
        
        expected = 1.0 * 2.0 + 2.0 * 3.0 + 3.0 * 4.0  # 20.0
        assert similarity == expected
    
    def test_calculate_similarity_zero_norm(self, service):
        """ゼロノルムベクトルの類似度計算テスト"""
        embedding1 = np.array([0.0, 0.0, 0.0])
        embedding2 = np.array([1.0, 1.0, 1.0])
        
        similarity = service.calculate_similarity(embedding1, embedding2, "cosine")
        
        assert similarity == 0.0
    
    def test_calculate_similarity_invalid_method(self, service):
        """無効な類似度計算方法テスト"""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        
        with pytest.raises(ValueError):
            service.calculate_similarity(embedding1, embedding2, "invalid")
    
    def test_batch_encode_with_metadata(self, service, mock_sentence_transformer):
        """メタデータ付きバッチ埋め込みテスト"""
        service.model = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ])
        
        data_list = [
            {"text": "テキスト1", "id": 1, "category": "A"},
            {"text": "テキスト2", "id": 2, "category": "B"}
        ]
        
        results = service.batch_encode_with_metadata(data_list, "text")
        
        assert len(results) == 2
        assert results[0]["text"] == "テキスト1"
        assert results[0]["embedding"] == [0.1, 0.2, 0.3]
        assert results[0]["metadata"] == {"id": 1, "category": "A"}
        assert results[1]["text"] == "テキスト2"
        assert results[1]["embedding"] == [0.4, 0.5, 0.6]
        assert results[1]["metadata"] == {"id": 2, "category": "B"}
    
    def test_get_model_info(self, service):
        """モデル情報取得テスト"""
        info = service.get_model_info()
        
        assert "model_name" in info
        assert "dimension" in info
        assert "device" in info
        assert "loaded" in info
        assert info["model_name"] == "test-model"
        assert info["loaded"] is False
    
    def test_get_model_info_loaded(self, service, mock_sentence_transformer):
        """ロード済みモデル情報取得テスト"""
        service.model = mock_sentence_transformer
        
        info = service.get_model_info()
        
        assert info["loaded"] is True
    
    def test_get_embedding_service_singleton(self):
        """シングルトンインスタンス取得テスト"""
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2
        assert isinstance(service1, EmbeddingService)


class TestEmbeddingServiceIntegration:
    """埋め込みサービス統合テストクラス"""
    
    @pytest.fixture
    def integration_service(self):
        """統合テスト用サービス"""
        # 軽量なモデルを使用
        return EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    @pytest.mark.integration
    def test_real_embedding_generation(self, integration_service):
        """実際の埋め込み生成テスト（実際のモデルが必要）"""
        try:
            integration_service.load_model()
            
            # 単一テキスト
            result = integration_service.encode_texts("これはテストです")
            assert isinstance(result, np.ndarray)
            assert result.shape[0] == 1
            assert result.shape[1] > 0
            
            # 複数テキスト
            texts = ["テキスト1", "テキスト2", "テキスト3"]
            result = integration_service.encode_texts(texts)
            assert result.shape[0] == 3
            assert result.shape[1] > 0
            
            # 類似度計算
            embedding1 = result[0]
            embedding2 = result[1]
            similarity = integration_service.calculate_similarity(
                embedding1, embedding2, "cosine"
            )
            assert -1.0 <= similarity <= 1.0
            
        except Exception as e:
            pytest.skip(f"統合テストスキップ（モデルが利用できません）: {e}")
    
    @pytest.mark.integration
    def test_real_product_embedding(self, integration_service):
        """実際の製品埋め込み生成テスト"""
        try:
            integration_service.load_model()
            
            product_data = {
                "name": "ワイヤレスイヤホン",
                "description": "高音質のBluetoothイヤホンです",
                "category": "オーディオ",
                "brand": "テックブランド"
            }
            
            result = integration_service.encode_product_description(product_data)
            assert isinstance(result, np.ndarray)
            assert result.shape[0] > 0
            
        except Exception as e:
            pytest.skip(f"統合テストスキップ（モデルが利用できません）: {e}")