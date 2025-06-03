from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
import uuid # For example generation

from src.data_models.reporting_models import EffectivenessReport, MetricValue
from src.services.analytics_service import AnalyticsService
# To fetch action plan details, we'd typically use SuggestionRepository or SuggestionService
from src.repositories.suggestion_repository import SuggestionRepository
# Assuming core exceptions are standard
from src.core.exceptions import NotFoundException, ServiceException

class EffectivenessReportingService:
    def __init__(self,
                 analytics_service: AnalyticsService,
                 suggestion_repository: SuggestionRepository): # Inject SuggestionRepository
        self.analytics_service = analytics_service
        self.suggestion_repository = suggestion_repository

    async def _get_product_data_for_period(self, product_name: str, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Helper to fetch and process product data for a specific product and period."""
        # Calculate days for analytics service call based on period
        # This is a simplification; in reality, the analytics service might take date ranges.
        # For now, we assume 'days' param for get_comprehensive_dashboard is sufficient if we align it.
        # This helper might need direct access to more granular analytics fetching if available.

        # For simplicity, we'll use the 'days' parameter of get_comprehensive_dashboard.
        # This implies the dashboard data is fetched relative to 'now' for 'days'.
        # A more accurate implementation would have analytics methods that accept date ranges.
        # Let's assume for this placeholder that 'days' roughly corresponds to the period length.
        period_duration_days = (end_date - start_date).days
        if period_duration_days <=0: return None # Or handle error

        try:
            # This is a simplification: get_comprehensive_dashboard usually fetches for 'last N days'.
            # We'd ideally have an analytics method that takes date ranges.
            # For this example, we'll fetch a general dashboard and try to find the product.
            # This part is highly dependent on the actual capabilities of AnalyticsService.
            # Let's assume the 'days' parameter can be used somewhat flexibly or that
            # the dashboard contains enough historical data to filter.
            # A more robust solution would be:
            # analytics_data = await self.analytics_service.get_product_metrics_for_period(
            # product_name_or_id, start_date, end_date)

            # Simplified: Fetch general dashboard for a period that *includes* our target range
            # then filter. This is inefficient but works with current AnalyticsService mock structure.
            # We'll use a 'days' value that ensures our period is covered, assuming data is daily.
            # This is a placeholder for more precise data fetching.
            days_for_fetch = (datetime.utcnow().date() - start_date.date()).days + 1
            if days_for_fetch <= 0: days_for_fetch = period_duration_days # fallback

            analytics = await self.analytics_service.get_comprehensive_dashboard(days=days_for_fetch)
            if not analytics or "product_analytics" not in analytics:
                return None
            products_data = analytics["product_analytics"].get("products_data", [])
            for p_data in products_data:
                if isinstance(p_data, dict) and p_data.get("product_name") == product_name:
                    # This simplified example assumes the dashboard data for the period
                    # directly gives the metrics for that product for the *entire fetched range*.
                    # A real implementation would need the analytics service to provide
                    # aggregated metrics for the *specific start/end dates*.
                    # For now, we'll use this as a mock placeholder.
                    return {
                        "total_revenue": p_data.get("total_revenue", 0),
                        "units_sold": p_data.get("units_sold", 0)
                    }
            return None # Product not found in this simplified fetch
        except Exception as e:
            print(f"Error fetching analytics for {product_name} for period {start_date}-{end_date}: {e}")
            return None


    async def generate_report_for_action_plan(
        self,
        action_plan_id: str,
        reporting_period_start: datetime,
        reporting_period_end: datetime,
        baseline_period_start: Optional[datetime] = None,
        baseline_period_end: Optional[datetime] = None,
        generated_by: Optional[str] = None
    ) -> Optional[EffectivenessReport]:
        """
        Generates an effectiveness report for a given action plan and reporting period.
        """
        action_plan = await self.suggestion_repository.get_action_plan_by_id(action_plan_id)
        if not action_plan:
            raise NotFoundException(f"ActionPlan with id {action_plan_id} not found.")

        # Simplified: Infer target entity (e.g., product name) from action plan title
        # This is a placeholder. A real system would have explicit links or metadata.
        target_product_name = None
        if "product" in action_plan.title.lower(): # Very naive inference
            parts = action_plan.title.split(":")
            if len(parts) > 1:
                potential_name = parts[-1].strip()
                # Further parsing might be needed if it's like "Action Plan for [Product Name]"
                if "Action Plan for " in potential_name: # Assuming format "Action Plan for ProductX"
                    target_product_name = potential_name.replace("Action Plan for ", "").strip()
                else: # Assuming format "Action Plan for ProductX"
                    target_product_name = potential_name

        if not target_product_name:
            # Cannot determine target entity for metrics, return basic report or raise
            print(f"Warning: Could not determine target entity from action plan title: {action_plan.title}")
            # Fallback to a generic report or raise error
            return EffectivenessReport(
                report_title=f"Effectiveness Report for: {action_plan.title}",
                action_plan_id=action_plan_id,
                action_plan_title=action_plan.title,
                reporting_period_start=reporting_period_start,
                reporting_period_end=reporting_period_end,
                summary="Could not automatically determine target entity for detailed metric comparison.",
                generated_by=generated_by or "system"
            )

        key_metrics_for_report: List[MetricValue] = []
        summary_parts = []

        # Fetch data for reporting period
        reporting_data = await self._get_product_data_for_period(
            target_product_name, reporting_period_start, reporting_period_end
        )

        baseline_data = None
        if baseline_period_start and baseline_period_end:
            baseline_data = await self._get_product_data_for_period(
                target_product_name, baseline_period_start, baseline_period_end
            )

        # Metric 1: Sales Revenue
        if reporting_data and "total_revenue" in reporting_data:
            reporting_revenue = reporting_data["total_revenue"]
            metric_revenue = MetricValue(
                metric_name=f"Sales Revenue ({target_product_name})",
                value=reporting_revenue,
                unit="USD"
            )
            change_note_revenue = f"Reporting period revenue: {reporting_revenue} USD."
            if baseline_data and "total_revenue" in baseline_data:
                baseline_revenue = baseline_data["total_revenue"]
                metric_revenue.notes = f"Baseline revenue: {baseline_revenue} USD."
                change_note_revenue += f" Baseline: {baseline_revenue} USD."
                if baseline_revenue > 0:
                    change_pct = ((reporting_revenue - baseline_revenue) / baseline_revenue) * 100
                    metric_revenue.change_from_baseline = round(change_pct, 2)
                    change_note_revenue += f" Change: {metric_revenue.change_from_baseline}%."
            summary_parts.append(change_note_revenue)
            key_metrics_for_report.append(metric_revenue)

        # Metric 2: Units Sold
        if reporting_data and "units_sold" in reporting_data:
            reporting_units = reporting_data["units_sold"]
            metric_units = MetricValue(
                metric_name=f"Units Sold ({target_product_name})",
                value=reporting_units,
                unit="count"
            )
            change_note_units = f"Reporting period units sold: {reporting_units}."
            if baseline_data and "units_sold" in baseline_data:
                baseline_units = baseline_data["units_sold"]
                metric_units.notes = f"Baseline units sold: {baseline_units}."
                change_note_units += f" Baseline: {baseline_units}."
                if baseline_units > 0:
                    change_pct = ((reporting_units - baseline_units) / baseline_units) * 100
                    metric_units.change_from_baseline = round(change_pct, 2)
                    change_note_units += f" Change: {metric_units.change_from_baseline}%."
            summary_parts.append(change_note_units)
            key_metrics_for_report.append(metric_units)

        final_summary = " ".join(summary_parts)
        if not key_metrics_for_report:
            final_summary = f"No specific product metrics found for '{target_product_name}' in the reporting period. Action plan title: {action_plan.title}"


        report = EffectivenessReport(
            report_title=f"Effectiveness Report for: {action_plan.title}",
            action_plan_id=action_plan_id,
            action_plan_title=action_plan.title,
                reporting_period_start=reporting_period_start,
                reporting_period_end=reporting_period_end,
                baseline_period_start=baseline_period_start,
                baseline_period_end=baseline_period_end,
                key_metrics=key_metrics_for_report,
                summary=final_summary or "Report generated, but specific metrics for comparison were not available or applicable based on action plan title.",
                generated_by=generated_by or "system"
            )
        return report

    async def get_report_by_id(self, report_id: str) -> Optional[EffectivenessReport]:
        """
        Retrieves a specific effectiveness report by its ID.
        Placeholder - returns example or None.
        """
        # In a real implementation, this would fetch from a database
        if report_id == "existing_report_uuid_xyz":
             return EffectivenessReport(
                id=report_id,
                report_title="Sample Report Detail",
                action_plan_id=str(uuid.uuid4()), # Dummy
                action_plan_title="Action Plan for Q1 Sales Boost",
                reporting_period_start=datetime.utcnow() - timedelta(days=30),
                reporting_period_end=datetime.utcnow(),
                key_metrics=[MetricValue(metric_name="Website Traffic", value=15000, unit="views")],
                summary="This is a sample detailed report fetched by ID.",
                generated_by="system_test"
            )
        return None

    async def list_reports_for_action_plan(self, action_plan_id: str) -> List[EffectivenessReport]:
        """
        Lists all effectiveness reports generated for a specific action plan.
        Placeholder - returns empty list or example.
        """
        # In a real implementation, this would query a database
        if action_plan_id == "existing_plan_for_report_abc": # Known ID for example
            return [
                EffectivenessReport(
                    id=str(uuid.uuid4()),
                    report_title=f"Report 1 for Action Plan: Example Plan",
                    action_plan_id=action_plan_id,
                    action_plan_title="Example Action Plan Title",
                    reporting_period_start=datetime.utcnow() - timedelta(days=60),
                    reporting_period_end=datetime.utcnow() - timedelta(days=30),
                    key_metrics=[MetricValue(metric_name="Engagement", value=0.75)],
                    summary="Initial report.",
                    generated_by="system_test"
                )
            ]
        return []

    # Additional methods might include:
    # - schedule_report_generation(...)
    # - delete_report(...)
    # - list_all_reports_paginated(...)
