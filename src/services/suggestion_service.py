from typing import List, Optional, Dict, Any
import uuid # For generating example IDs
from datetime import datetime

from src.data_models.suggestion_models import Suggestion, ActionPlan, ActionPlanStep, SuggestionWithActionPlan
from src.services.analytics_service import AnalyticsService
from src.services.client_preference_service import ClientPreferenceService
# Assuming core exceptions are now the standard for service layer
from src.core.exceptions import NotFoundException, ServiceException, DatabaseException
from src.repositories.suggestion_repository import SuggestionRepository # Import new repository
from src.neo4j_utils.connector import Neo4jConnector # For instantiating repo if needed by service itself

class SuggestionService:
    def __init__(self,
                 analytics_service: AnalyticsService,
                 client_preference_service: ClientPreferenceService,
                 suggestion_repository: SuggestionRepository): # Inject repository
        self.analytics_service = analytics_service
        self.client_preference_service = client_preference_service
        self.suggestion_repository = suggestion_repository

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
        # for item in churn_suggestions: # Persist these as well
        #     await self.suggestion_repository.save_suggestion_with_plan(item, created_by_user_id=client_id) # Assuming client_id as user context
        # suggestions_with_plans.extend(churn_suggestions)

        # Rule 3: Opportunities from Top Performing Segments (CRM)
        # crm_opportunity_suggestions = self._check_crm_opportunities(analytics_data, client_preferences)
        # for item in crm_opportunity_suggestions: # Persist these as well
        #     await self.suggestion_repository.save_suggestion_with_plan(item, created_by_user_id=client_id)
        # suggestions_with_plans.extend(crm_opportunity_suggestions)

        # After generating all, save them. (Or save one by one if preferred)
        # For simplicity, let's assume the service generates them and then they are saved if needed by a controller,
        # or if saving is intrinsic to generation:
        for item in suggestions_with_plans:
            try:
                # Assuming client_id can serve as a proxy for created_by_user_id in this context
                await self.suggestion_repository.save_suggestion_with_plan(item, created_by_user_id=client_id)
            except DatabaseException as e:
                # Log the error, decide if we should continue saving others or raise
                print(f"Error saving suggestion {item.suggestion.id} for client {client_id}: {e}")
                # Potentially collect failures and report them, or raise a consolidated error.
                # For now, we'll let it try to save others.

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
        try:
            return await self.suggestion_repository.get_suggestion_with_plan_by_id(suggestion_id)
        except DatabaseException as e:
            # Log error
            print(f"Database error fetching suggestion details for {suggestion_id}: {e}")
            raise ServiceException(f"Could not retrieve suggestion details for {suggestion_id}.") from e
        except Exception as e: # Catch any other unexpected errors
            print(f"Unexpected error fetching suggestion details for {suggestion_id}: {e}")
            raise ServiceException(f"An unexpected error occurred while fetching suggestion {suggestion_id}.") from e


    async def update_action_plan_step_status(self, action_plan_id: str, step_id: str, new_status: str, updated_by_user_id: str) -> Optional[ActionPlan]:
        """
        Updates the status of a specific step within an action plan.
        """
        try:
            action_plan = await self.suggestion_repository.get_action_plan_by_id(action_plan_id)
            if not action_plan:
                raise NotFoundException(f"ActionPlan with id {action_plan_id} not found.")

            found_step = False
            for step in action_plan.steps:
                if step.step_id == step_id:
                    step.status = new_status
                    found_step = True
                    break

            if not found_step:
                raise NotFoundException(f"Step with id {step_id} not found in action plan {action_plan_id}.")

            # Update overall_status of the ActionPlan based on step statuses
            # Example: if all steps are "completed", plan is "completed".
            # If any step is "in_progress", plan is "in_progress".
            # If all are "pending" or "deferred" (and none in_progress/completed), plan is "pending".
            # This logic can be more sophisticated.
            if all(s.status == "completed" for s in action_plan.steps):
                action_plan.overall_status = "completed"
            elif any(s.status == "in_progress" for s in action_plan.steps):
                action_plan.overall_status = "in_progress"
            elif all(s.status in ["pending", "deferred"] for s in action_plan.steps):
                 action_plan.overall_status = "pending"
            else: # Mixed, could be 'in_progress' or a more specific partial status
                action_plan.overall_status = "in_progress"


            action_plan.updated_at = datetime.utcnow()
            # updated_by_user_id will be set by the repository during the update call

            updated_plan = await self.suggestion_repository.update_action_plan(action_plan, updated_by_user_id)
            return updated_plan

        except NotFoundException: # Re-raise NotFoundExceptions from this service
            raise
        except DatabaseException as e:
            print(f"Database error updating action plan step for plan {action_plan_id}, step {step_id}: {e}")
            raise ServiceException(f"Could not update action plan step for plan {action_plan_id}.") from e
        except Exception as e:
            print(f"Unexpected error updating action plan step for plan {action_plan_id}, step {step_id}: {e}")
            raise ServiceException(f"An unexpected error occurred while updating action plan step.") from e


    # Other methods might include:
    # - list_suggestions_for_client(client_id: str)
    # - get_action_plan_for_suggestion(suggestion_id: str)
    # - create_custom_suggestion_or_action_plan(...)
    # - etc.
