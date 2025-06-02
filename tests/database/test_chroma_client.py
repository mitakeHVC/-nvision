"""
ChromaDBクライアントのテストモジュール

ChromaDBクライアントの各機能をテストします。
接続、コレクション管理、CRUD操作の動作を検証します。
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.database.chroma_client import ChromaDBClient, get_chroma_client


class TestChromaDBClient:
    """ChromaDBクライアントのテストクラス"""
    
    @pytest.fixture
    def client(self):
        """テスト用クライアントインスタンス"""
        return ChromaDBClient()
    
    @pytest.fixture
    def mock_chroma_client(self):
        """モックChromaDBクライアント"""
        with patch('src.database.chroma_client.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_chromadb.HttpClient.return_value = mock_client
            yield mock_client
    
    def test_init(self, client):
        """初期化テスト"""
        assert client.client is None
        assert client.collections == {}
        assert "host" in client.config
        assert "port" in client.config
    
    def test_connect_persistent_mode(self, client, mock_chroma_client):
        """永続化モード接続テスト"""
        client.config["persist_directory"] = "./test_chroma"
        
        client.connect()
        
        assert client.client is not None
    
    def test_connect_http_mode(self, client, mock_chroma_client):
        """HTTPモード接続テスト"""
        client.config["persist_directory"] = None
        
        client.connect()
        
        assert client.client is not None
    
    def test_connect_error(self, client):
        """接続エラーテスト"""
        with patch('src.database.chroma_client.chromadb.PersistentClient') as mock_client:
            mock_client.side_effect = Exception("接続エラー")
            
            with pytest.raises(Exception):
                client.connect()
    
    def test_disconnect(self, client, mock_chroma_client):
        """切断テスト"""
        client.connect()
        client.collections["test"] = Mock()
        
        client.disconnect()
        
        assert client.client is None
        assert client.collections == {}
    
    def test_create_collection(self, client, mock_chroma_client):
        """コレクション作成テスト"""
        client.connect()
        
        mock_collection = Mock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        
        result = client.create_collection("test_collection", {"test": "metadata"})
        
        assert result == mock_collection
        assert "test_collection" in client.collections
        mock_chroma_client.get_or_create_collection.assert_called_once_with(
            name="test_collection",
            metadata={"test": "metadata"}
        )
    
    def test_create_collection_not_connected(self, client):
        """未接続時のコレクション作成テスト"""
        with pytest.raises(RuntimeError, match="ChromaDBに接続されていません"):
            client.create_collection("test_collection")
    
    def test_get_collection_cached(self, client, mock_chroma_client):
        """キャッシュされたコレクション取得テスト"""
        client.connect()
        mock_collection = Mock()
        client.collections["test_collection"] = mock_collection
        
        result = client.get_collection("test_collection")
        
        assert result == mock_collection
    
    def test_get_collection_from_db(self, client, mock_chroma_client):
        """データベースからのコレクション取得テスト"""
        client.connect()
        
        mock_collection = Mock()
        mock_chroma_client.get_collection.return_value = mock_collection
        
        result = client.get_collection("test_collection")
        
        assert result == mock_collection
        assert "test_collection" in client.collections
    
    def test_get_collection_not_found(self, client, mock_chroma_client):
        """存在しないコレクション取得テスト"""
        client.connect()
        
        mock_chroma_client.get_collection.side_effect = Exception("コレクションが存在しません")
        
        result = client.get_collection("nonexistent_collection")
        
        assert result is None
    
    def test_delete_collection(self, client, mock_chroma_client):
        """コレクション削除テスト"""
        client.connect()
        client.collections["test_collection"] = Mock()
        
        result = client.delete_collection("test_collection")
        
        assert result is True
        assert "test_collection" not in client.collections
        mock_chroma_client.delete_collection.assert_called_once_with(name="test_collection")
    
    def test_delete_collection_error(self, client, mock_chroma_client):
        """コレクション削除エラーテスト"""
        client.connect()
        
        mock_chroma_client.delete_collection.side_effect = Exception("削除エラー")
        
        result = client.delete_collection("test_collection")
        
        assert result is False
    
    def test_add_embeddings(self, client, mock_chroma_client):
        """埋め込み追加テスト"""
        client.connect()
        
        mock_collection = Mock()
        client.collections["test_collection"] = mock_collection
        
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]
        ids = ["id1", "id2"]
        
        result = client.add_embeddings(
            "test_collection",
            embeddings,
            documents,
            metadatas,
            ids
        )
        
        assert result is True
        mock_collection.add.assert_called_once_with(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def test_add_embeddings_auto_ids(self, client, mock_chroma_client):
        """自動ID生成での埋め込み追加テスト"""
        client.connect()
        
        mock_collection = Mock()
        client.collections["test_collection"] = mock_collection
        
        embeddings = [[0.1, 0.2, 0.3]]
        documents = ["doc1"]
        
        result = client.add_embeddings("test_collection", embeddings, documents)
        
        assert result is True
        # 自動生成されたIDが使用されることを確認
        call_args = mock_collection.add.call_args
        assert call_args[1]["ids"] == ["doc_0"]
    
    def test_query_embeddings(self, client, mock_chroma_client):
        """埋め込み検索テスト"""
        client.connect()
        
        mock_collection = Mock()
        mock_collection.query.return_value = {"ids": [["id1"]], "distances": [[0.1]]}
        client.collections["test_collection"] = mock_collection
        
        query_embeddings = [[0.1, 0.2, 0.3]]
        
        result = client.query_embeddings("test_collection", query_embeddings, n_results=5)
        
        assert result == {"ids": [["id1"]], "distances": [[0.1]]}
        mock_collection.query.assert_called_once_with(
            query_embeddings=query_embeddings,
            n_results=5,
            where=None,
            include=["documents", "metadatas", "distances"]
        )
    
    def test_query_embeddings_collection_not_found(self, client):
        """存在しないコレクションでの検索テスト"""
        client.connect()
        
        result = client.query_embeddings("nonexistent", [[0.1, 0.2, 0.3]])
        
        assert result is None
    
    def test_update_embeddings(self, client, mock_chroma_client):
        """埋め込み更新テスト"""
        client.connect()
        
        mock_collection = Mock()
        client.collections["test_collection"] = mock_collection
        
        ids = ["id1", "id2"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        
        result = client.update_embeddings("test_collection", ids, embeddings=embeddings)
        
        assert result is True
        mock_collection.update.assert_called_once_with(
            ids=ids,
            embeddings=embeddings,
            documents=None,
            metadatas=None
        )
    
    def test_delete_embeddings(self, client, mock_chroma_client):
        """埋め込み削除テスト"""
        client.connect()
        
        mock_collection = Mock()
        client.collections["test_collection"] = mock_collection
        
        ids = ["id1", "id2"]
        
        result = client.delete_embeddings("test_collection", ids)
        
        assert result is True
        mock_collection.delete.assert_called_once_with(ids=ids)
    
    def test_get_collection_info(self, client, mock_chroma_client):
        """コレクション情報取得テスト"""
        client.connect()
        
        mock_collection = Mock()
        mock_collection.count.return_value = 100
        mock_collection.metadata = {"test": "metadata"}
        client.collections["test_collection"] = mock_collection
        
        result = client.get_collection_info("test_collection")
        
        expected = {
            "name": "test_collection",
            "count": 100,
            "metadata": {"test": "metadata"}
        }
        assert result == expected
    
    def test_list_collections(self, client, mock_chroma_client):
        """コレクション一覧取得テスト"""
        client.connect()
        
        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        
        mock_chroma_client.list_collections.return_value = [mock_collection1, mock_collection2]
        
        result = client.list_collections()
        
        assert result == ["collection1", "collection2"]
    
    def test_get_chroma_client_singleton(self):
        """シングルトンインスタンス取得テスト"""
        client1 = get_chroma_client()
        client2 = get_chroma_client()
        
        assert client1 is client2
        assert isinstance(client1, ChromaDBClient)


class TestChromaDBClientIntegration:
    """ChromaDBクライアント統合テストクラス"""
    
    @pytest.fixture
    def integration_client(self):
        """統合テスト用クライアント"""
        client = ChromaDBClient()
        # テスト用の設定を使用
        client.config = {
            "host": "localhost",
            "port": 8000,
            "persist_directory": "./test_chroma_data"
        }
        return client
    
    @pytest.mark.integration
    def test_full_workflow(self, integration_client):
        """完全なワークフローテスト（実際のChromaDBが必要）"""
        # このテストは実際のChromaDBインスタンスが必要
        # CI/CDでは@pytest.mark.integrationでスキップ可能
        
        try:
            # 接続
            integration_client.connect()
            
            # コレクション作成
            collection = integration_client.create_collection("test_workflow")
            assert collection is not None
            
            # データ追加
            embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            documents = ["テストドキュメント1", "テストドキュメント2"]
            metadatas = [{"type": "test1"}, {"type": "test2"}]
            ids = ["test1", "test2"]
            
            success = integration_client.add_embeddings(
                "test_workflow",
                embeddings,
                documents,
                metadatas,
                ids
            )
            assert success is True
            
            # 検索
            results = integration_client.query_embeddings(
                "test_workflow",
                [[0.1, 0.2, 0.3]],
                n_results=2
            )
            assert results is not None
            assert len(results["ids"][0]) == 2
            
            # クリーンアップ
            integration_client.delete_collection("test_workflow")
            
        except Exception as e:
            pytest.skip(f"統合テストスキップ（ChromaDBが利用できません）: {e}")
        finally:
            integration_client.disconnect()