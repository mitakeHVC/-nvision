#!/usr/bin/env python3
"""
nvisionプロジェクトの診断テストスクリプト
Phase 1で発見された問題を詳細に診断します。
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_python_environment():
    """Python環境の診断"""
    logger.info("=== Python環境診断 ===")
    logger.info(f"Python バージョン: {sys.version}")
    logger.info(f"Python 実行パス: {sys.executable}")
    logger.info(f"現在の作業ディレクトリ: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {sys.path}")

def test_package_imports():
    """パッケージインポートの診断"""
    logger.info("=== パッケージインポート診断 ===")
    
    packages = [
        'pytest',
        'pydantic',
        'chromadb',
        'neo4j',
        'sentence_transformers',
        'transformers',
        'torch',
        'numpy',
        'pandas'
    ]
    
    for package in packages:
        try:
            __import__(package)
            logger.info(f"✓ {package}: インポート成功")
        except ImportError as e:
            logger.error(f"✗ {package}: インポート失敗 - {e}")
        except Exception as e:
            logger.error(f"✗ {package}: 予期しないエラー - {e}")

def test_pydantic_version():
    """Pydantic バージョンの診断"""
    logger.info("=== Pydantic バージョン診断 ===")
    
    try:
        import pydantic
        logger.info(f"Pydantic バージョン: {pydantic.VERSION}")
        
        # Pydantic v2の機能をテスト
        try:
            from pydantic_settings import BaseSettings
            logger.info("✓ Pydantic v2 BaseSettings: 利用可能")
        except ImportError:
            logger.warning("✗ Pydantic v2 BaseSettings: 利用不可")
            
        # Pydantic v1の機能をテスト
        try:
            from pydantic import BaseSettings as V1BaseSettings
            logger.info("✓ Pydantic v1 BaseSettings: 利用可能")
        except ImportError:
            logger.warning("✗ Pydantic v1 BaseSettings: 利用不可")
            
    except Exception as e:
        logger.error(f"Pydantic診断エラー: {e}")

def test_config_loading():
    """設定ファイルの読み込み診断"""
    logger.info("=== 設定ファイル診断 ===")
    
    try:
        from src.config.database_config import DatabaseConfig, db_config
        logger.info("✓ DatabaseConfig: インポート成功")
        
        # 設定値の確認
        logger.info(f"Neo4j URI: {db_config.neo4j_uri}")
        logger.info(f"ChromaDB Host: {db_config.chroma_host}")
        logger.info(f"ChromaDB Port: {db_config.chroma_port}")
        logger.info(f"ChromaDB Persist Directory: {db_config.chroma_persist_directory}")
        logger.info(f"Embedding Model: {db_config.embedding_model_name}")
        
    except Exception as e:
        logger.error(f"設定ファイル読み込みエラー: {e}")
        logger.error(traceback.format_exc())

def test_chromadb_connection():
    """ChromaDB接続の診断"""
    logger.info("=== ChromaDB接続診断 ===")
    
    try:
        import chromadb
        logger.info(f"ChromaDB バージョン: {chromadb.__version__}")
        
        # 永続化クライアントのテスト
        try:
            client = chromadb.PersistentClient(path="./test_chroma_data")
            logger.info("✓ ChromaDB PersistentClient: 作成成功")
            
            # テストコレクションの作成
            collection = client.get_or_create_collection("test_collection")
            logger.info("✓ ChromaDB Collection: 作成成功")
            
            # クリーンアップ
            client.delete_collection("test_collection")
            logger.info("✓ ChromaDB Collection: 削除成功")
            
        except Exception as e:
            logger.error(f"ChromaDB PersistentClient エラー: {e}")
            
        # HTTPクライアントのテスト（サーバーが起動していない場合は失敗する）
        try:
            http_client = chromadb.HttpClient(host="localhost", port=8000)
            logger.info("✓ ChromaDB HttpClient: 作成成功")
        except Exception as e:
            logger.warning(f"ChromaDB HttpClient エラー（サーバー未起動の可能性）: {e}")
            
    except Exception as e:
        logger.error(f"ChromaDB診断エラー: {e}")
        logger.error(traceback.format_exc())

def test_neo4j_connection():
    """Neo4j接続の診断"""
    logger.info("=== Neo4j接続診断 ===")
    
    try:
        from neo4j import GraphDatabase
        logger.info("✓ Neo4j ドライバー: インポート成功")
        
        # 接続テスト（サーバーが起動していない場合は失敗する）
        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "password")
            )
            
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record["test"] == 1:
                    logger.info("✓ Neo4j接続: 成功")
                else:
                    logger.error("✗ Neo4j接続: 予期しない結果")
                    
            driver.close()
            
        except Exception as e:
            logger.warning(f"Neo4j接続エラー（サーバー未起動の可能性）: {e}")
            
    except Exception as e:
        logger.error(f"Neo4j診断エラー: {e}")
        logger.error(traceback.format_exc())

def test_embedding_service():
    """埋め込みサービスの診断"""
    logger.info("=== 埋め込みサービス診断 ===")
    
    try:
        from src.services.embedding_service import EmbeddingService
        logger.info("✓ EmbeddingService: インポート成功")
        
        # サービスの初期化
        service = EmbeddingService()
        logger.info("✓ EmbeddingService: 初期化成功")
        
        # モデル情報の取得
        info = service.get_model_info()
        logger.info(f"モデル名: {info['model_name']}")
        logger.info(f"デバイス: {info['device']}")
        logger.info(f"ロード状態: {info['loaded']}")
        
        # 軽量なテストのため、モデルの実際のロードはスキップ
        logger.info("注意: モデルの実際のロードはスキップしました")
        
    except Exception as e:
        logger.error(f"埋め込みサービス診断エラー: {e}")
        logger.error(traceback.format_exc())

def test_chroma_client():
    """ChromaDBクライアントの診断"""
    logger.info("=== ChromaDBクライアント診断 ===")
    
    try:
        from src.database.chroma_client import ChromaDBClient
        logger.info("✓ ChromaDBClient: インポート成功")
        
        # クライアントの初期化
        client = ChromaDBClient()
        logger.info("✓ ChromaDBClient: 初期化成功")
        
        # 接続テスト
        client.connect()
        logger.info("✓ ChromaDBClient: 接続成功")
        
        # テストコレクションの作成
        collection = client.create_collection("diagnostic_test")
        logger.info("✓ ChromaDBClient: コレクション作成成功")
        
        # コレクション情報の取得
        info = client.get_collection_info("diagnostic_test")
        logger.info(f"コレクション情報: {info}")
        
        # クリーンアップ
        client.delete_collection("diagnostic_test")
        logger.info("✓ ChromaDBClient: コレクション削除成功")
        
        client.disconnect()
        logger.info("✓ ChromaDBClient: 切断成功")
        
    except Exception as e:
        logger.error(f"ChromaDBクライアント診断エラー: {e}")
        logger.error(traceback.format_exc())

def main():
    """メイン診断関数"""
    logger.info("nvisionプロジェクト診断テスト開始")
    logger.info("=" * 50)
    
    # 各診断テストを実行
    test_python_environment()
    test_package_imports()
    test_pydantic_version()
    test_config_loading()
    test_chromadb_connection()
    test_neo4j_connection()
    test_embedding_service()
    test_chroma_client()
    
    logger.info("=" * 50)
    logger.info("nvisionプロジェクト診断テスト完了")

if __name__ == "__main__":
    main()