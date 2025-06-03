"""
レコメンデーションサービス

製品推薦とパーソナライゼーション機能を提供
"""

from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from ..repositories.customer_repository import CustomerRepository
from ..repositories.product_repository import ProductRepository
from ..repositories.order_repository import OrderRepository
from ..repositories.vector_repository import VectorRepository
from ..data_models.ec_models import Customer, Product, Order

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    レコメンデーションサービス
    
    顧客の購買履歴と行動データに基づく製品推薦
    """
    
    def __init__(self):
        """サービスの初期化"""
        self.customer_repository = CustomerRepository()
        self.product_repository = ProductRepository()
        self.order_repository = OrderRepository()
        self.vector_repository = VectorRepository()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_recommendations_for_customer(
        self, 
        customer_id: int, 
        limit: int = 10,
        recommendation_type: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        顧客向けの製品推薦を取得
        
        Args:
            customer_id: 顧客ID
            limit: 推薦製品数
            recommendation_type: 推薦タイプ（collaborative, content, hybrid）
            
        Returns:
            推薦製品のリスト
        """
        try:
            self.logger.info(f"Getting recommendations for customer {customer_id}, type: {recommendation_type}")
            
            # 顧客の存在確認
            customer = await self.customer_repository.get_by_customer_id(customer_id)
            if not customer:
                self.logger.warning(f"Customer not found: {customer_id}")
                return []
            
            recommendations = []
            
            if recommendation_type == "collaborative":
                recommendations = await self._collaborative_filtering(customer_id, limit)
            elif recommendation_type == "content":
                recommendations = await self._content_based_filtering(customer_id, limit)
            else:  # hybrid
                recommendations = await self._hybrid_recommendations(customer_id, limit)
            
            self.logger.info(f"Generated {len(recommendations)} recommendations for customer {customer_id}")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to get recommendations for customer {customer_id}: {e}")
            raise
    
    async def get_similar_products(self, product_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        類似製品を取得
        
        Args:
            product_id: 基準となる製品ID
            limit: 取得する類似製品数
            
        Returns:
            類似製品のリスト
        """
        try:
            self.logger.info(f"Getting similar products for product {product_id}")
            
            # 基準製品を取得
            base_product = await self.product_repository.get_by_product_id(product_id)
            if not base_product:
                self.logger.warning(f"Product not found: {product_id}")
                return []
            
            # ベクトル検索で類似製品を取得
            query_text = f"{base_product.ProductName} {base_product.Description or ''}"
            
            search_results = await self.vector_repository.search_similar(
                collection_type="products",
                query_text=query_text,
                n_results=limit + 1  # 自分自身を除くため+1
            )
            
            similar_products = []
            for result in search_results:
                result_product_id = result.metadata.get("product_id")
                
                # 自分自身は除外
                if result_product_id == product_id:
                    continue
                
                # 製品詳細を取得
                product = await self.product_repository.get_by_product_id(result_product_id)
                if product:
                    similar_products.append({
                        "product": product,
                        "similarity_score": result.similarity,
                        "reason": "類似した特徴を持つ製品"
                    })
                
                if len(similar_products) >= limit:
                    break
            
            self.logger.info(f"Found {len(similar_products)} similar products")
            return similar_products
            
        except Exception as e:
            self.logger.error(f"Failed to get similar products for {product_id}: {e}")
            raise
    
    async def get_trending_products(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        トレンド製品を取得
        
        Args:
            days: 集計期間（日数）
            limit: 取得する製品数
            
        Returns:
            トレンド製品のリスト
        """
        try:
            self.logger.info(f"Getting trending products for last {days} days")
            
            # 期間の設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 期間内の注文を取得
            orders = await self.order_repository.get_by_date_range(start_date, end_date)
            
            # 製品別の注文回数を集計
            product_counts = defaultdict(int)
            product_quantities = defaultdict(int)
            
            for order in orders:
                order_items = await self.order_repository.get_order_items(order.OrderID)
                for item in order_items:
                    if item.ProductID:
                        product_counts[item.ProductID] += 1
                        product_quantities[item.ProductID] += item.Quantity or 0
            
            # トレンドスコアを計算（注文回数 + 数量の重み付け）
            trending_scores = {}
            for product_id in product_counts:
                order_count = product_counts[product_id]
                quantity = product_quantities[product_id]
                trending_scores[product_id] = order_count * 2 + quantity
            
            # スコア順にソート
            sorted_products = sorted(trending_scores.items(), key=lambda x: x[1], reverse=True)
            
            # 製品詳細を取得
            trending_products = []
            for product_id, score in sorted_products[:limit]:
                product = await self.product_repository.get_by_product_id(product_id)
                if product:
                    trending_products.append({
                        "product": product,
                        "trending_score": score,
                        "order_count": product_counts[product_id],
                        "total_quantity": product_quantities[product_id],
                        "reason": f"過去{days}日間で{product_counts[product_id]}回注文された人気商品"
                    })
            
            self.logger.info(f"Found {len(trending_products)} trending products")
            return trending_products
            
        except Exception as e:
            self.logger.error(f"Failed to get trending products: {e}")
            raise
    
    async def get_frequently_bought_together(self, product_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        一緒に購入される製品を取得
        
        Args:
            product_id: 基準となる製品ID
            limit: 取得する製品数
            
        Returns:
            一緒に購入される製品のリスト
        """
        try:
            self.logger.info(f"Getting frequently bought together for product {product_id}")
            
            # 基準製品を含む注文を取得
            all_orders = await self.order_repository.get_all()
            target_orders = []
            
            for order in all_orders:
                order_items = await self.order_repository.get_order_items(order.OrderID)
                product_ids = [item.ProductID for item in order_items if item.ProductID]
                
                if product_id in product_ids:
                    target_orders.append(order_items)
            
            # 一緒に購入された製品を集計
            co_purchased = defaultdict(int)
            
            for order_items in target_orders:
                product_ids = [item.ProductID for item in order_items if item.ProductID and item.ProductID != product_id]
                
                for pid in product_ids:
                    co_purchased[pid] += 1
            
            # 頻度順にソート
            sorted_products = sorted(co_purchased.items(), key=lambda x: x[1], reverse=True)
            
            # 製品詳細を取得
            frequently_bought = []
            for pid, count in sorted_products[:limit]:
                product = await self.product_repository.get_by_product_id(pid)
                if product:
                    confidence = count / len(target_orders) if target_orders else 0
                    frequently_bought.append({
                        "product": product,
                        "co_purchase_count": count,
                        "confidence": confidence,
                        "reason": f"{count}回一緒に購入されています"
                    })
            
            self.logger.info(f"Found {len(frequently_bought)} frequently bought together products")
            return frequently_bought
            
        except Exception as e:
            self.logger.error(f"Failed to get frequently bought together for {product_id}: {e}")
            raise
    
    async def get_personalized_categories(self, customer_id: int) -> List[Dict[str, Any]]:
        """
        顧客の好みカテゴリを取得
        
        Args:
            customer_id: 顧客ID
            
        Returns:
            好みカテゴリのリスト
        """
        try:
            self.logger.info(f"Getting personalized categories for customer {customer_id}")
            
            # 顧客の注文履歴を取得
            orders = await self.order_repository.get_by_customer_id(customer_id)
            
            # カテゴリ別の購入回数を集計
            category_counts = defaultdict(int)
            category_amounts = defaultdict(float)
            
            for order in orders:
                order_items = await self.order_repository.get_order_items(order.OrderID)
                
                for item in order_items:
                    if item.ProductID:
                        product = await self.product_repository.get_by_product_id(item.ProductID)
                        if product and product.CategoryID:
                            category_counts[product.CategoryID] += 1
                            category_amounts[product.CategoryID] += item.TotalPrice or 0
            
            # カテゴリ情報を整理
            personalized_categories = []
            for category_id, count in category_counts.items():
                amount = category_amounts[category_id]
                avg_amount = amount / count if count > 0 else 0
                
                personalized_categories.append({
                    "category_id": category_id,
                    "purchase_count": count,
                    "total_amount": amount,
                    "average_amount": avg_amount,
                    "preference_score": count * 2 + (amount / 1000)  # 簡単なスコア計算
                })
            
            # スコア順にソート
            personalized_categories.sort(key=lambda x: x["preference_score"], reverse=True)
            
            self.logger.info(f"Found {len(personalized_categories)} personalized categories")
            return personalized_categories
            
        except Exception as e:
            self.logger.error(f"Failed to get personalized categories for customer {customer_id}: {e}")
            raise
    
    async def _collaborative_filtering(self, customer_id: int, limit: int) -> List[Dict[str, Any]]:
        """
        協調フィルタリングによる推薦
        
        Args:
            customer_id: 顧客ID
            limit: 推薦製品数
            
        Returns:
            推薦製品のリスト
        """
        try:
            # 顧客の購入履歴を取得
            customer_orders = await self.order_repository.get_by_customer_id(customer_id)
            customer_products = set()
            
            for order in customer_orders:
                order_items = await self.order_repository.get_order_items(order.OrderID)
                for item in order_items:
                    if item.ProductID:
                        customer_products.add(item.ProductID)
            
            # 類似顧客を見つける
            all_orders = await self.order_repository.get_all()
            customer_similarities = {}
            
            for order in all_orders:
                if order.CustomerID and order.CustomerID != customer_id:
                    order_items = await self.order_repository.get_order_items(order.OrderID)
                    other_products = set(item.ProductID for item in order_items if item.ProductID)
                    
                    # Jaccard類似度を計算
                    intersection = customer_products.intersection(other_products)
                    union = customer_products.union(other_products)
                    similarity = len(intersection) / len(union) if union else 0
                    
                    if similarity > 0:
                        if order.CustomerID not in customer_similarities:
                            customer_similarities[order.CustomerID] = similarity
                        else:
                            customer_similarities[order.CustomerID] = max(customer_similarities[order.CustomerID], similarity)
            
            # 類似顧客の購入製品を推薦
            recommendations = []
            similar_customers = sorted(customer_similarities.items(), key=lambda x: x[1], reverse=True)[:5]
            
            recommended_products = defaultdict(float)
            
            for similar_customer_id, similarity in similar_customers:
                similar_orders = await self.order_repository.get_by_customer_id(similar_customer_id)
                
                for order in similar_orders:
                    order_items = await self.order_repository.get_order_items(order.OrderID)
                    for item in order_items:
                        if item.ProductID and item.ProductID not in customer_products:
                            recommended_products[item.ProductID] += similarity
            
            # スコア順にソート
            sorted_recommendations = sorted(recommended_products.items(), key=lambda x: x[1], reverse=True)
            
            for product_id, score in sorted_recommendations[:limit]:
                product = await self.product_repository.get_by_product_id(product_id)
                if product:
                    recommendations.append({
                        "product": product,
                        "recommendation_score": score,
                        "reason": "類似した購買傾向の顧客が購入した商品"
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Collaborative filtering failed: {e}")
            return []
    
    async def _content_based_filtering(self, customer_id: int, limit: int) -> List[Dict[str, Any]]:
        """
        コンテンツベースフィルタリングによる推薦
        
        Args:
            customer_id: 顧客ID
            limit: 推薦製品数
            
        Returns:
            推薦製品のリスト
        """
        try:
            # 顧客の購入履歴から好みを分析
            customer_orders = await self.order_repository.get_by_customer_id(customer_id)
            purchased_products = []
            
            for order in customer_orders:
                order_items = await self.order_repository.get_order_items(order.OrderID)
                for item in order_items:
                    if item.ProductID:
                        product = await self.product_repository.get_by_product_id(item.ProductID)
                        if product:
                            purchased_products.append(product)
            
            if not purchased_products:
                return []
            
            # 購入製品の特徴を基にベクトル検索
            recommendations = []
            used_product_ids = set(p.ProductID for p in purchased_products)
            
            for product in purchased_products[-3:]:  # 最近の3製品を基準
                query_text = f"{product.ProductName} {product.Description or ''}"
                
                search_results = await self.vector_repository.search_similar(
                    collection_type="products",
                    query_text=query_text,
                    n_results=limit * 2
                )
                
                for result in search_results:
                    result_product_id = result.metadata.get("product_id")
                    
                    if result_product_id not in used_product_ids:
                        similar_product = await self.product_repository.get_by_product_id(result_product_id)
                        if similar_product:
                            recommendations.append({
                                "product": similar_product,
                                "recommendation_score": result.similarity,
                                "reason": f"「{product.ProductName}」と類似した特徴を持つ商品"
                            })
                            used_product_ids.add(result_product_id)
                    
                    if len(recommendations) >= limit:
                        break
                
                if len(recommendations) >= limit:
                    break
            
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Content-based filtering failed: {e}")
            return []
    
    async def _hybrid_recommendations(self, customer_id: int, limit: int) -> List[Dict[str, Any]]:
        """
        ハイブリッド推薦（協調フィルタリング + コンテンツベース）
        
        Args:
            customer_id: 顧客ID
            limit: 推薦製品数
            
        Returns:
            推薦製品のリスト
        """
        try:
            # 協調フィルタリングとコンテンツベースの結果を取得
            collaborative_recs = await self._collaborative_filtering(customer_id, limit)
            content_recs = await self._content_based_filtering(customer_id, limit)
            
            # スコアを統合
            combined_scores = {}
            
            # 協調フィルタリングの結果（重み: 0.6）
            for rec in collaborative_recs:
                product_id = rec["product"].ProductID
                combined_scores[product_id] = {
                    "product": rec["product"],
                    "score": rec["recommendation_score"] * 0.6,
                    "reasons": [rec["reason"]]
                }
            
            # コンテンツベースの結果（重み: 0.4）
            for rec in content_recs:
                product_id = rec["product"].ProductID
                if product_id in combined_scores:
                    combined_scores[product_id]["score"] += rec["recommendation_score"] * 0.4
                    combined_scores[product_id]["reasons"].append(rec["reason"])
                else:
                    combined_scores[product_id] = {
                        "product": rec["product"],
                        "score": rec["recommendation_score"] * 0.4,
                        "reasons": [rec["reason"]]
                    }
            
            # スコア順にソート
            sorted_recommendations = sorted(
                combined_scores.values(),
                key=lambda x: x["score"],
                reverse=True
            )
            
            # 結果を整形
            recommendations = []
            for rec in sorted_recommendations[:limit]:
                recommendations.append({
                    "product": rec["product"],
                    "recommendation_score": rec["score"],
                    "reason": " / ".join(rec["reasons"])
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Hybrid recommendations failed: {e}")
            return []