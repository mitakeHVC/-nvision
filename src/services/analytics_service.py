"""
分析サービス

ビジネス分析とレポート機能を提供
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from ..repositories.customer_repository import CustomerRepository
from ..repositories.product_repository import ProductRepository
from ..repositories.order_repository import OrderRepository
from ..repositories.crm_repository import CRMRepository
from ..data_models.ec_models import Customer, Product, Order

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    分析サービス
    
    売上分析、顧客分析、製品分析などのビジネス分析機能
    """
    
    def __init__(self):
        """サービスの初期化"""
        self.customer_repository = CustomerRepository()
        self.product_repository = ProductRepository()
        self.order_repository = OrderRepository()
        self.crm_repository = CRMRepository()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_sales_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        売上分析を取得
        
        Args:
            days: 分析期間（日数）
            
        Returns:
            売上分析データ
        """
        try:
            self.logger.info(f"Getting sales analytics for last {days} days")
            
            # 期間の設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 期間内の注文を取得
            orders = await self.order_repository.get_by_date_range(start_date, end_date)
            
            # 基本統計
            total_orders = len(orders)
            total_revenue = sum(order.TotalAmount or 0 for order in orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            # 日別売上
            daily_sales = defaultdict(float)
            daily_orders = defaultdict(int)
            
            for order in orders:
                if order.OrderDate:
                    date_key = order.OrderDate.date().isoformat()
                    daily_sales[date_key] += order.TotalAmount or 0
                    daily_orders[date_key] += 1
            
            # 成長率計算（前期間との比較）
            prev_start = start_date - timedelta(days=days)
            prev_orders = await self.order_repository.get_by_date_range(prev_start, start_date)
            prev_revenue = sum(order.TotalAmount or 0 for order in prev_orders)
            
            growth_rate = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
            
            # ステータス別分析
            status_breakdown = defaultdict(lambda: {"count": 0, "amount": 0})
            for order in orders:
                status = order.OrderStatus or "未設定"
                status_breakdown[status]["count"] += 1
                status_breakdown[status]["amount"] += order.TotalAmount or 0
            
            analytics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "summary": {
                    "total_orders": total_orders,
                    "total_revenue": total_revenue,
                    "average_order_value": avg_order_value,
                    "growth_rate": growth_rate
                },
                "daily_breakdown": {
                    "sales": dict(daily_sales),
                    "orders": dict(daily_orders)
                },
                "status_breakdown": dict(status_breakdown),
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Sales analytics generated: {total_orders} orders, {total_revenue} revenue")
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get sales analytics: {e}")
            raise
    
    async def get_customer_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        顧客分析を取得
        
        Args:
            days: 分析期間（日数）
            
        Returns:
            顧客分析データ
        """
        try:
            self.logger.info(f"Getting customer analytics for last {days} days")
            
            # 期間の設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 全顧客と期間内の注文を取得
            all_customers = await self.customer_repository.get_all()
            orders = await self.order_repository.get_by_date_range(start_date, end_date)
            
            # 新規顧客数
            new_customers = await self.customer_repository.get_recent_customers(days)
            
            # 顧客別の購入分析
            customer_stats = defaultdict(lambda: {"orders": 0, "amount": 0, "last_order": None})
            
            for order in orders:
                if order.CustomerID:
                    customer_stats[order.CustomerID]["orders"] += 1
                    customer_stats[order.CustomerID]["amount"] += order.TotalAmount or 0
                    
                    if not customer_stats[order.CustomerID]["last_order"] or order.OrderDate > customer_stats[order.CustomerID]["last_order"]:
                        customer_stats[order.CustomerID]["last_order"] = order.OrderDate
            
            # 顧客セグメント分析
            active_customers = len(customer_stats)
            repeat_customers = len([c for c in customer_stats.values() if c["orders"] > 1])
            
            # 顧客生涯価値（CLV）の簡易計算
            total_customer_value = sum(stats["amount"] for stats in customer_stats.values())
            avg_customer_value = total_customer_value / active_customers if active_customers > 0 else 0
            
            # 顧客獲得コスト（仮想値）
            customer_acquisition_cost = 5000  # 仮の値
            
            # RFM分析の簡易版
            rfm_segments = await self._calculate_rfm_segments(customer_stats, end_date)
            
            analytics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "summary": {
                    "total_customers": len(all_customers),
                    "new_customers": len(new_customers),
                    "active_customers": active_customers,
                    "repeat_customers": repeat_customers,
                    "repeat_rate": (repeat_customers / active_customers * 100) if active_customers > 0 else 0
                },
                "value_metrics": {
                    "average_customer_value": avg_customer_value,
                    "customer_acquisition_cost": customer_acquisition_cost,
                    "customer_lifetime_value": avg_customer_value * 2.5  # 簡易CLV
                },
                "rfm_segments": rfm_segments,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Customer analytics generated: {active_customers} active customers")
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get customer analytics: {e}")
            raise
    
    async def get_product_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        製品分析を取得
        
        Args:
            days: 分析期間（日数）
            
        Returns:
            製品分析データ
        """
        try:
            self.logger.info(f"Getting product analytics for last {days} days")
            
            # 期間の設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 全製品と期間内の注文を取得
            all_products = await self.product_repository.get_all()
            orders = await self.order_repository.get_by_date_range(start_date, end_date)
            
            # 製品別の売上分析
            product_stats = defaultdict(lambda: {"orders": 0, "quantity": 0, "revenue": 0})
            
            for order in orders:
                order_items = await self.order_repository.get_order_items(order.OrderID)
                
                for item in order_items:
                    if item.ProductID:
                        product_stats[item.ProductID]["orders"] += 1
                        product_stats[item.ProductID]["quantity"] += item.Quantity or 0
                        product_stats[item.ProductID]["revenue"] += item.TotalPrice or 0
            
            # トップ製品の特定
            top_products_by_revenue = sorted(
                product_stats.items(),
                key=lambda x: x[1]["revenue"],
                reverse=True
            )[:10]
            
            top_products_by_quantity = sorted(
                product_stats.items(),
                key=lambda x: x[1]["quantity"],
                reverse=True
            )[:10]
            
            # 製品詳細を取得
            top_revenue_details = []
            for product_id, stats in top_products_by_revenue:
                product = await self.product_repository.get_by_product_id(product_id)
                if product:
                    top_revenue_details.append({
                        "product": product,
                        "stats": stats
                    })
            
            top_quantity_details = []
            for product_id, stats in top_products_by_quantity:
                product = await self.product_repository.get_by_product_id(product_id)
                if product:
                    top_quantity_details.append({
                        "product": product,
                        "stats": stats
                    })
            
            # カテゴリ別分析
            category_stats = defaultdict(lambda: {"products": 0, "revenue": 0, "quantity": 0})
            
            for product in all_products:
                category_id = product.CategoryID or 0
                category_stats[category_id]["products"] += 1
                
                if product.ProductID in product_stats:
                    stats = product_stats[product.ProductID]
                    category_stats[category_id]["revenue"] += stats["revenue"]
                    category_stats[category_id]["quantity"] += stats["quantity"]
            
            # 在庫分析
            inventory_analysis = await self._analyze_inventory(all_products)
            
            analytics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "summary": {
                    "total_products": len(all_products),
                    "products_sold": len(product_stats),
                    "total_quantity_sold": sum(stats["quantity"] for stats in product_stats.values()),
                    "total_product_revenue": sum(stats["revenue"] for stats in product_stats.values())
                },
                "top_products": {
                    "by_revenue": top_revenue_details,
                    "by_quantity": top_quantity_details
                },
                "category_breakdown": dict(category_stats),
                "inventory_analysis": inventory_analysis,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Product analytics generated: {len(product_stats)} products sold")
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get product analytics: {e}")
            raise
    
    async def get_crm_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        CRM分析を取得
        
        Args:
            days: 分析期間（日数）
            
        Returns:
            CRM分析データ
        """
        try:
            self.logger.info(f"Getting CRM analytics for last {days} days")
            
            # 期間の設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # CRMデータを取得
            all_contacts = await self.crm_repository.get_all()
            contacts = [entity for entity in all_contacts if hasattr(entity, 'ContactID')]
            companies = [entity for entity in all_contacts if hasattr(entity, 'CompanyID')]
            deals = [entity for entity in all_contacts if hasattr(entity, 'DealID')]
            interactions = [entity for entity in all_contacts if hasattr(entity, 'InteractionID')]
            
            # 最近のインタラクション
            recent_interactions = await self.crm_repository.get_recent_interactions(days)
            
            # 商談パイプライン分析
            pipeline_summary = await self.crm_repository.get_deal_pipeline_summary()
            
            # 活動分析
            activity_summary = await self.crm_repository.get_activity_summary(days)
            
            # 商談ステージ別分析
            stage_analysis = defaultdict(lambda: {"count": 0, "amount": 0})
            for deal in deals:
                if hasattr(deal, 'Stage') and hasattr(deal, 'Amount'):
                    stage = deal.Stage or "未設定"
                    stage_analysis[stage]["count"] += 1
                    stage_analysis[stage]["amount"] += deal.Amount or 0
            
            # 営業担当者別分析
            user_analysis = defaultdict(lambda: {"deals": 0, "interactions": 0, "deal_amount": 0})
            
            for deal in deals:
                if hasattr(deal, 'AssignedToUserID') and deal.AssignedToUserID:
                    user_analysis[deal.AssignedToUserID]["deals"] += 1
                    user_analysis[deal.AssignedToUserID]["deal_amount"] += deal.Amount or 0
            
            for interaction in recent_interactions:
                if hasattr(interaction, 'AssignedToUserID') and interaction.AssignedToUserID:
                    user_analysis[interaction.AssignedToUserID]["interactions"] += 1
            
            analytics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "summary": {
                    "total_contacts": len(contacts),
                    "total_companies": len(companies),
                    "total_deals": len(deals),
                    "recent_interactions": len(recent_interactions)
                },
                "pipeline_analysis": pipeline_summary,
                "activity_analysis": activity_summary,
                "stage_breakdown": dict(stage_analysis),
                "user_performance": dict(user_analysis),
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"CRM analytics generated: {len(deals)} deals, {len(recent_interactions)} interactions")
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get CRM analytics: {e}")
            raise
    
    async def get_comprehensive_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """
        包括的なダッシュボードデータを取得
        
        Args:
            days: 分析期間（日数）
            
        Returns:
            ダッシュボードデータ
        """
        try:
            self.logger.info(f"Getting comprehensive dashboard for last {days} days")
            
            # 各分析を並行して取得
            sales_analytics = await self.get_sales_analytics(days)
            customer_analytics = await self.get_customer_analytics(days)
            product_analytics = await self.get_product_analytics(days)
            crm_analytics = await self.get_crm_analytics(days)
            
            # KPIサマリー
            kpi_summary = {
                "revenue": sales_analytics["summary"]["total_revenue"],
                "orders": sales_analytics["summary"]["total_orders"],
                "customers": customer_analytics["summary"]["active_customers"],
                "products_sold": product_analytics["summary"]["products_sold"],
                "deals": crm_analytics["summary"]["total_deals"],
                "growth_rate": sales_analytics["summary"]["growth_rate"]
            }
            
            dashboard = {
                "period": {
                    "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
                    "end_date": datetime.now().isoformat(),
                    "days": days
                },
                "kpi_summary": kpi_summary,
                "sales": sales_analytics,
                "customers": customer_analytics,
                "products": product_analytics,
                "crm": crm_analytics,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info("Comprehensive dashboard generated successfully")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to get comprehensive dashboard: {e}")
            raise
    
    async def _calculate_rfm_segments(self, customer_stats: Dict, end_date: datetime) -> Dict[str, Any]:
        """
        RFMセグメント分析を計算
        
        Args:
            customer_stats: 顧客統計データ
            end_date: 分析終了日
            
        Returns:
            RFMセグメント分析結果
        """
        try:
            if not customer_stats:
                return {}
            
            # RFMスコアを計算
            rfm_data = []
            for customer_id, stats in customer_stats.items():
                recency = (end_date - stats["last_order"]).days if stats["last_order"] else 999
                frequency = stats["orders"]
                monetary = stats["amount"]
                
                rfm_data.append({
                    "customer_id": customer_id,
                    "recency": recency,
                    "frequency": frequency,
                    "monetary": monetary
                })
            
            # 簡易セグメント分類
            segments = {"Champions": 0, "Loyal": 0, "Potential": 0, "At Risk": 0, "Lost": 0}
            
            for data in rfm_data:
                if data["recency"] <= 30 and data["frequency"] >= 3 and data["monetary"] >= 50000:
                    segments["Champions"] += 1
                elif data["recency"] <= 60 and data["frequency"] >= 2:
                    segments["Loyal"] += 1
                elif data["recency"] <= 90 and data["frequency"] == 1:
                    segments["Potential"] += 1
                elif data["recency"] <= 180:
                    segments["At Risk"] += 1
                else:
                    segments["Lost"] += 1
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Failed to calculate RFM segments: {e}")
            return {}
    
    async def _analyze_inventory(self, products: List[Product]) -> Dict[str, Any]:
        """
        在庫分析を実行
        
        Args:
            products: 製品リスト
            
        Returns:
            在庫分析結果
        """
        try:
            total_products = len(products)
            total_stock = sum(p.StockQuantity or 0 for p in products)
            total_value = sum((p.Price or 0) * (p.StockQuantity or 0) for p in products)
            
            # 在庫状況別の分類
            out_of_stock = len([p for p in products if (p.StockQuantity or 0) == 0])
            low_stock = len([p for p in products if 0 < (p.StockQuantity or 0) <= 10])
            normal_stock = len([p for p in products if (p.StockQuantity or 0) > 10])
            
            return {
                "total_products": total_products,
                "total_stock_units": total_stock,
                "total_inventory_value": total_value,
                "stock_status": {
                    "out_of_stock": out_of_stock,
                    "low_stock": low_stock,
                    "normal_stock": normal_stock
                },
                "average_stock_per_product": total_stock / total_products if total_products > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze inventory: {e}")
            return {}