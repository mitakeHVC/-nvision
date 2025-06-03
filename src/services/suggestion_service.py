from typing import List, Optional, Dict, Any
import uuid # For generating example IDs
from datetime import datetime

from src.data_models.suggestion_models import Suggestion, ActionPlan, ActionPlanStep, SuggestionWithActionPlan
from src.services.analytics_service import AnalyticsService
from src.services.client_preference_service import ClientPreferenceService
# Assuming core exceptions are now the standard for service layer
from src.core.exceptions import NotFoundException, ServiceException

class SuggestionService:
    def __init__(self, analytics_service: AnalyticsService, client_preference_service: ClientPreferenceService):
        self.analytics_service = analytics_service
        self.client_preference_service = client_preference_service

    async def generate_suggestions(self, client_id: str, days: int = 30) -> List[SuggestionWithActionPlan]:
        """
        Generates insights and actionable suggestions based on client preferences and analytics data.
        """
        suggestions_with_plans: List[SuggestionWithActionPlan] = []

        # 1. Fetch client preferences
        client_preferences = await self.client_preference_service.get_preferences_by_client_id(client_id)
        if not client_preferences or not client_preferences.preferences_payload:
            # Log warning or handle as per business rule (e.g., return empty list, default suggestions)
            print(f"Warning: Client preferences not found or empty for client_id: {client_id}")
            # Depending on requirements, might raise NotFoundException or return default/no suggestions
            # For now, let's proceed, and rules will check for specific preference keys.
            pass # Allow to proceed, rules will check for specific preference keys

        # 2. Fetch comprehensive analytics
        # analytics_data = await self.analytics_service.get_comprehensive_dashboard(days=days)

        # 2. Fetch comprehensive analytics
        try:
            analytics_data = await self.analytics_service.get_comprehensive_dashboard(days=days)
        except Exception as e:
            # Log error from analytics service
            print(f"Error fetching analytics data: {e}")
            # Depending on requirements, might raise ServiceException or return empty list
            return [] # Or raise ServiceException("Could not retrieve analytics data for suggestions.")

        if not analytics_data:
            print(f"Warning: No analytics data returned for client_id: {client_id}, days: {days}")
            return []

        # 3. Implement logic to derive suggestions
        # Rule 1: Low-Performing Products with High Inventory
        product_suggestions = self._check_product_inventory_mismatch(analytics_data, client_preferences)
        suggestions_with_plans.extend(product_suggestions)

        # Rule 2: High Customer Churn Rate (if available)
        # churn_suggestions = self._check_customer_churn(analytics_data, client_preferences)
        # suggestions_with_plans.extend(churn_suggestions)

        # Rule 3: Opportunities from Top Performing Segments (CRM)
        # crm_opportunity_suggestions = self._check_crm_opportunities(analytics_data, client_preferences)
        # suggestions_with_plans.extend(crm_opportunity_suggestions)

        return suggestions_with_plans

    def _check_product_inventory_mismatch(self, analytics_data: Dict[str, Any], client_preferences: Optional[Any]) -> List[SuggestionWithActionPlan]:
        """
        Identifies low-performing products with high inventory.
        ClientPreference type is 'Any' because it's not strictly typed in its model yet beyond Dict.
        """
        generated_suggestions: List[SuggestionWithActionPlan] = []

        # Check if client is interested in this type of suggestion
        # Assuming preferences_payload is a dict.
        prefs_payload = client_preferences.preferences_payload if client_preferences else {}
        interested_in_inventory = "inventory_optimization" in prefs_payload.get("target_areas", [])
        interested_in_sales_imp = "sales_improvement" in prefs_payload.get("target_areas", [])

        if not (interested_in_inventory or interested_in_sales_imp):
            return generated_suggestions

        product_analytics = analytics_data.get("product_analytics")
        if not product_analytics or not isinstance(product_analytics, dict):
            return generated_suggestions

        all_products_data = product_analytics.get("products_data", []) # Assuming products_data is a list of dicts
        if not all_products_data:
            return generated_suggestions

        # Example thresholds (these should be configurable or dynamically determined)
        # For "low sales", let's consider products in the bottom 20th percentile by revenue.
        # For "high inventory", let's consider products with stock > 50 (arbitrary).

        if not all_products_data: return generated_suggestions

        # Sort products by sales revenue to find bottom 20%
        # Assuming each product dict has 'product_id', 'product_name', 'total_revenue', 'stock_quantity'
        try:
            # Filter out products that might be missing essential data for this rule
            valid_products = [p for p in all_products_data if isinstance(p, dict) and \
                              "total_revenue" in p and "stock_quantity" in p and "product_name" in p and "product_id" in p]

            if not valid_products: return generated_suggestions

            valid_products.sort(key=lambda x: x.get("total_revenue", 0))
            num_products = len(valid_products)
            bottom_20_percentile_index = int(num_products * 0.2)
            low_sales_products = valid_products[:bottom_20_percentile_index]

            high_inventory_threshold = 50 # Example static threshold

            for product in low_sales_products:
                stock_quantity = product.get("stock_quantity", 0)
                if stock_quantity > high_inventory_threshold:
                    suggestion_id = str(uuid.uuid4())
                    product_name = product.get("product_name", "N/A")
                    sales_metric = product.get("total_revenue", "N/A")

                    suggestion = Suggestion(
                        id=suggestion_id,
                        title=f"Review Low-Performing Product: {product_name}",
                        description=f"{product_name} has low sales (revenue: {sales_metric}) but high inventory ({stock_quantity} units). Consider promotional activities or re-evaluating its market fit.",
                        source_analysis_type="product_inventory_sales_mismatch",
                        severity="medium",
                        related_data_points=[
                            {"product_id": product.get("product_id")},
                            {"metric": "Total Revenue", "value": sales_metric},
                            {"metric": "Stock Quantity", "value": stock_quantity}
                        ],
                        potential_impact="Addressing this could free up capital, reduce holding costs, and potentially boost sales for this or other items.",
                    )
                    action_plan = ActionPlan(
                        id=str(uuid.uuid4()),
                        suggestion_id=suggestion_id,
                        title=f"Action Plan for {product_name}",
                        overview=f"Address low sales and high inventory for {product_name}.",
                        steps=[
                            ActionPlanStep(description=f"Analyze reasons for low sales of {product_name} (market trends, pricing, visibility, customer reviews).", responsible_area="Marketing/Sales", status="pending"),
                            ActionPlanStep(description=f"Develop and implement a targeted promotion or clearance strategy for {product_name}.", responsible_area="Marketing", status="pending")
                        ]
                    )
                    generated_suggestions.append(SuggestionWithActionPlan(suggestion=suggestion, action_plan=action_plan))

        except Exception as e:
            # Log this error, e.g. if product data is not in expected format
            print(f"Error processing product inventory mismatch rule: {e}")
            # Continue to other rules or return generated_suggestions so far

        return generated_suggestions

    def _check_customer_churn(self, analytics_data: Dict[str, Any], client_preferences: Optional[Any]) -> List[SuggestionWithActionPlan]:
        """
        Identifies high customer churn rate based on analytics and client preferences.
        Placeholder - returns empty list.
        """
        generated_suggestions: List[SuggestionWithActionPlan] = []
        prefs_payload = client_preferences.preferences_payload if client_preferences else {}

        if "customer_retention" not in prefs_payload.get("target_areas", []):
            return generated_suggestions

        # Example Logic (to be replaced with actual analysis)
        # customer_analytics = analytics_data.get("customer_analytics")
        # if customer_analytics and customer_analytics.get("churn_rate_high", False): # Assuming a boolean flag or specific metric
        #     suggestion_id = str(uuid.uuid4())
        #     suggestion = Suggestion(
        #         id=suggestion_id,
        #         title="Investigate High Customer Churn Rate",
        #         description="Customer analytics indicate a potentially high churn rate or low repeat purchase rate. Further investigation is recommended to identify causes and implement retention strategies.",
        #         source_analysis_type="customer_churn_analysis",
        #         severity="high",
        #         related_data_points=[{"metric": "Churn Rate Indicator", "value": "High"}], # Replace with actual metric
        #         potential_impact="Reducing churn can significantly improve customer lifetime value and overall revenue."
        #     )
        #     action_plan = ActionPlan(
        #         id=str(uuid.uuid4()),
        #         suggestion_id=suggestion_id,
        #         title="Address Customer Churn",
        #         overview="Develop and implement strategies to improve customer retention.",
        #         steps=[
        #             ActionPlanStep(description="Conduct customer exit surveys or analyze feedback from churned customers.", responsible_area="CX/Marketing", status="pending"),
        #             ActionPlanStep(description="Review CRM interactions for common complaints or issues leading to churn.", responsible_area="Support/Sales", status="pending"),
        #             ActionPlanStep(description="Develop a targeted re-engagement campaign for at-risk customers.", responsible_area="Marketing", status="pending")
        #         ]
        #     )
        #     generated_suggestions.append(SuggestionWithActionPlan(suggestion=suggestion, action_plan=action_plan))
        return generated_suggestions

    def _check_crm_opportunities(self, analytics_data: Dict[str, Any], client_preferences: Optional[Any]) -> List[SuggestionWithActionPlan]:
        """
        Identifies opportunities from top-performing CRM segments.
        Placeholder - returns empty list.
        """
        generated_suggestions: List[SuggestionWithActionPlan] = []
        prefs_payload = client_preferences.preferences_payload if client_preferences else {}

        if not ("sales_optimization" in prefs_payload.get("target_areas", []) or \
                "lead_generation" in prefs_payload.get("target_areas", [])):
            return generated_suggestions

        # Example Logic (to be replaced with actual analysis)
        # crm_analytics = analytics_data.get("crm_analytics")
        # if crm_analytics and crm_analytics.get("top_lead_source"): # Assuming some structure
        #     top_source = crm_analytics["top_lead_source"].get("name", "N/A")
        #     conversion_rate = crm_analytics["top_lead_source"].get("conversion_rate", "N/A")
        #     suggestion_id = str(uuid.uuid4())
        #     suggestion = Suggestion(
        #         id=suggestion_id,
        #         title=f"Capitalize on High-Performing Leads from {top_source}",
        #         description=f"Leads from '{top_source}' show a high conversion rate of {conversion_rate}%. Consider allocating more resources or targeted campaigns to this area.",
        #         source_analysis_type="crm_segment_opportunity",
        #         severity="high",
        #         related_data_points=[
        #             {"lead_source": top_source},
        #             {"conversion_rate": conversion_rate}
        #         ]
        #     )
        #     action_plan = ActionPlan(
        #         id=str(uuid.uuid4()),
        #         suggestion_id=suggestion_id,
        #         title=f"Optimize Lead Generation via {top_source}",
        #         overview=f"Further invest in and tailor efforts for the '{top_source}' lead channel.",
        #         steps=[
        #             ActionPlanStep(description=f"Increase marketing budget/effort for the '{top_source}' channel.", responsible_area="Marketing", status="pending"),
        #             ActionPlanStep(description=f"Develop tailored marketing campaigns or content specific to leads from '{top_source}'.", responsible_area="Marketing/Content", status="pending")
        #         ]
        #     )
        #     generated_suggestions.append(SuggestionWithActionPlan(suggestion=suggestion, action_plan=action_plan))
        return generated_suggestions

    async def get_suggestion_details(self, suggestion_id: str) -> Optional[SuggestionWithActionPlan]:
        """
        Retrieves details for a specific suggestion, including its action plan.
        Placeholder implementation.
        """
        # In a real implementation, this would fetch from a database or cache
        # For now, return a hardcoded example if the ID matches, or None

        example_suggestion_id_to_match = "existing_suggestion_uuid_123" # A known UUID for testing

        if suggestion_id == example_suggestion_id_to_match:
            example_suggestion = Suggestion(
                id=suggestion_id,
                title="Example: High Cart Abandonment Rate",
                description="Customers are adding items to their cart but not completing purchases. Average cart abandonment rate is 75% for the last week.",
                source_analysis_type="conversion_funnel_analysis",
                severity="high",
                related_data_points=[{"metric": "Cart Abandonment Rate", "value": 75, "unit": "%"}],
                potential_impact="Reducing abandonment by 10% could increase revenue by $Y.",
            )
            example_action_plan = ActionPlan(
                suggestion_id=suggestion_id,
                title="Reduce Cart Abandonment",
                overview="Implement measures to encourage purchase completion.",
                steps=[ActionPlanStep(description="Offer a time-limited discount for abandoned carts via email.", responsible_area="Marketing")]
            )
            return SuggestionWithActionPlan(suggestion=example_suggestion, action_plan=example_action_plan)
        return None

    async def update_action_plan_step_status(self, action_plan_id: str, step_id: str, new_status: str) -> Optional[ActionPlan]:
        """
        Updates the status of a specific step within an action plan.
        Placeholder implementation.
        """
        # In a real implementation, this would fetch the action plan, update the step, save, and return.
        # For now, return a hardcoded example or None.

        example_action_plan_id_to_match = "existing_action_plan_uuid_abc" # A known UUID for testing

        if action_plan_id == example_action_plan_id_to_match:
            # Simulate finding and updating an action plan
            # This is highly simplified. A real version would load the actual plan.
            dummy_suggestion_id = str(uuid.uuid4())
            action_plan = ActionPlan(
                id=action_plan_id,
                suggestion_id=dummy_suggestion_id, # In reality, this would be the correct suggestion_id
                title="Sample Action Plan for Update",
                overview="This is an overview of the sample plan.",
                steps=[
                    ActionPlanStep(step_id="step1_uuid", description="Initial step", status="completed"),
                    ActionPlanStep(step_id=step_id, description="Step to be updated", status="pending"), # Old status
                    ActionPlanStep(step_id="step3_uuid", description="Another step", status="pending")
                ],
                overall_status="in_progress",
                updated_at=datetime.utcnow() # Update timestamp
            )

            found_step = False
            for step in action_plan.steps:
                if step.step_id == step_id:
                    step.status = new_status
                    found_step = True
                    break

            if not found_step:
                # If the step_id doesn't exist in this dummy plan
                # raise NotFoundException(f"Step with id {step_id} not found in action plan {action_plan_id}")
                return None

            # Potentially update overall_status based on step statuses
            # ... (logic to determine overall_status) ...

            return action_plan

        return None

    # Other methods might include:
    # - list_suggestions_for_client(client_id: str)
    # - get_action_plan_for_suggestion(suggestion_id: str)
    # - create_custom_suggestion_or_action_plan(...)
    # - etc.
