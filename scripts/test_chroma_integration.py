#!/usr/bin/env python3
"""
ChromaDB統合テストスクリプト
Phase 1実装の基本機能動作確認用
"""

import sys
import os
import numpy as np
from typing import List, Dict, Any
import logging

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.chroma_client import ChromaDBClient
from src.services.embedding_service import EmbeddingService
from src.services.vector_search_service import VectorSearchService

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChromaIntegrationTester:
    """ChromaDB統合テストクラス"""
    
    def __init__(self):
        self.chroma_client = None
        self.embedding_service = None
        self.vector_search_service = None
        self.test_results = []
    
    def run_all_tests(self) -> Dict[str, Any]:
        """全てのテストを実行"""
        logger.info("=== ChromaDB統合テスト開始 ===")
        
        tests = [
            ("ChromaDBクライアント接続テスト", self.test_chroma_connection),
            ("埋め込みサービス動作テスト", self.test_embedding_service),
            ("ベクトル検索サービス動作テスト", self.test_vector_search_service),
            ("サンプルデータ検索機能テスト", self.test_sample_data_search),
            ("パフォーマンステスト", self.test_performance),
        ]
        
        results = {
            "total_tests": len(tests),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        for test_name, test_func in tests:
            try:
                logger.info(f"実行中: {test_name}")
                result = test_func()
                if result["success"]:
                    results["passed"] += 1
                    logger.info(f"✅ {test_name}: 成功")
                else:
                    results["failed"] += 1
                    logger.error(f"❌ {test_name}: 失敗 - {result.get('error', '')}")
                
                results["details"].append({
                    "test_name": test_name,
                    "success": result["success"],
                    "details": result.get("details", ""),
                    "error": result.get("error", "")
                })
                
            except Exception as e:
                results["failed"] += 1
                logger.error(f"❌ {test_name}: 例外発生 - {str(e)}")
                results["details"].append({
                    "test_name": test_name,
                    "success": False,
                    "error": str(e)
                })
        
        logger.info("=== ChromaDB統合テスト完了 ===")
        logger.info(f"結果: {results['passed']}/{results['total_tests']} テスト成功")
        
        return results
    
    def test_chroma_connection(self) -> Dict[str, Any]:
        """ChromaDBクライアント接続テスト"""
        try:
            self.chroma_client = ChromaDBClient()
            
            # 接続テスト
            self.chroma_client.connect()
            
            # コレクション作成テスト
            test_collection = "test_connection"
            collection = self.chroma_client.create_collection(test_collection)
            if not collection:
                return {"success": False, "error": "テストコレクション作成失敗"}
            
            # コレクション削除
            success = self.chroma_client.delete_collection(test_collection)
            if not success:
                return {"success": False, "error": "テストコレクション削除失敗"}
            
            return {
                "success": True,
                "details": "ChromaDBクライアント接続成功、基本操作確認完了"
            }
            
        except Exception as e:
            return {"success": False, "error": f"接続エラー: {str(e)}"}
    
    def test_embedding_service(self) -> Dict[str, Any]:
        """埋め込みサービス動作テスト"""
        try:
            self.embedding_service = EmbeddingService()
            
            # テストテキスト
            test_texts = [
                "これはテスト用の製品説明です。",
                "高品質な商品をお届けします。",
                "お客様満足度向上を目指しています。"
            ]
            
            # 埋め込み生成テスト
            embeddings = self.embedding_service.encode_texts(test_texts)
            
            if embeddings is None or len(embeddings) == 0:
                return {"success": False, "error": "埋め込み生成失敗"}
            
            if len(embeddings) != len(test_texts):
                return {"success": False, "error": "埋め込み数がテキスト数と一致しない"}
            
            # 埋め込み次元確認
            embedding_dim = len(embeddings[0]) if len(embeddings) > 0 else 0
            
            return {
                "success": True,
                "details": f"埋め込み生成成功: {len(test_texts)}テキスト, 次元数: {embedding_dim}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"埋め込みサービスエラー: {str(e)}"}
    
    def test_vector_search_service(self) -> Dict[str, Any]:
        """ベクトル検索サービス動作テスト"""
        try:
            if not self.chroma_client:
                self.chroma_client = ChromaDBClient()
            if not self.embedding_service:
                self.embedding_service = EmbeddingService()
            
            self.vector_search_service = VectorSearchService()
            
            # 初期化テスト
            self.vector_search_service.initialize()
            
            return {
                "success": True,
                "details": "ベクトル検索サービス初期化成功"
            }
            
        except Exception as e:
            return {"success": False, "error": f"ベクトル検索サービスエラー: {str(e)}"}
    
    def test_sample_data_search(self) -> Dict[str, Any]:
        """サンプルデータでの検索機能テスト"""
        try:
            if not self.vector_search_service:
                return {"success": False, "error": "ベクトル検索サービスが初期化されていません"}
            
            # サンプル製品データ追加
            sample_products = [
                {
                    "product_id": "test_p1",
                    "name": "テスト製品1",
                    "description": "高品質なテスト製品です",
                    "category": "テストカテゴリ",
                    "brand": "テストブランド",
                    "price": 1000.0
                },
                {
                    "product_id": "test_p2", 
                    "name": "テスト製品2",
                    "description": "優れた性能のテスト製品",
                    "category": "テストカテゴリ",
                    "brand": "テストブランド",
                    "price": 2000.0
                }
            ]
            
            # 製品埋め込み追加
            add_result = self.vector_search_service.add_product_embeddings(sample_products)
            if not add_result:
                return {"success": False, "error": "サンプル製品データ追加失敗"}
            
            # 検索テスト
            search_results = self.vector_search_service.search_similar_products(
                "高品質な製品", n_results=5
            )
            
            if not isinstance(search_results, list):
                return {"success": False, "error": "検索結果が期待される形式ではありません"}
            
            return {
                "success": True,
                "details": f"サンプルデータ検索成功: {len(search_results)}件の結果"
            }
            
        except Exception as e:
            return {"success": False, "error": f"サンプルデータ検索エラー: {str(e)}"}
    
    def test_performance(self) -> Dict[str, Any]:
        """パフォーマンステスト"""
        try:
            import time
            
            if not self.embedding_service:
                self.embedding_service = EmbeddingService()
            
            # 大量テキストでの埋め込み生成性能テスト
            large_texts = [f"テスト製品{i}の説明文です。" for i in range(100)]
            
            start_time = time.time()
            embeddings = self.embedding_service.encode_texts(large_texts)
            end_time = time.time()
            
            embedding_time = end_time - start_time
            
            if embeddings is None or len(embeddings) != len(large_texts):
                return {"success": False, "error": "大量データ埋め込み生成失敗"}
            
            # 検索性能テスト（既存データがある場合）
            if self.vector_search_service:
                start_time = time.time()
                search_results = self.vector_search_service.search_similar_products(
                    "テスト製品", n_results=10
                )
                end_time = time.time()
                search_time = end_time - start_time
            else:
                search_time = 0
            
            return {
                "success": True,
                "details": f"パフォーマンステスト完了 - 埋め込み生成: {embedding_time:.2f}秒 (100テキスト), 検索: {search_time:.3f}秒"
            }
            
        except Exception as e:
            return {"success": False, "error": f"パフォーマンステストエラー: {str(e)}"}

def main():
    """メイン実行関数"""
    tester = ChromaIntegrationTester()
    results = tester.run_all_tests()
    
    print("\n" + "="*60)
    print("ChromaDB統合テスト結果サマリー")
    print("="*60)
    print(f"総テスト数: {results['total_tests']}")
    print(f"成功: {results['passed']}")
    print(f"失敗: {results['failed']}")
    print(f"成功率: {(results['passed']/results['total_tests']*100):.1f}%")
    
    print("\n詳細結果:")
    for detail in results['details']:
        status = "✅" if detail['success'] else "❌"
        print(f"{status} {detail['test_name']}")
        if detail.get('details'):
            print(f"   詳細: {detail['details']}")
        if detail.get('error'):
            print(f"   エラー: {detail['error']}")
    
    # 終了コード設定
    exit_code = 0 if results['failed'] == 0 else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()