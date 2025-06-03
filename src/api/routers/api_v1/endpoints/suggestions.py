from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException, status
from pydantic import BaseModel

from src.services.suggestion_service import SuggestionService
from src.services.analytics_service import AnalyticsService # For dependency injection
from src.services.client_preference_service import ClientPreferenceService # For dependency injection
from src.data_models.suggestion_models import SuggestionWithActionPlan, ActionPlan, Suggestion
from src.auth.dependencies import get_current_active_user, require_permission
from src.auth.permissions import Permission # Will add new permissions (SUGGESTION_READ, ACTION_PLAN_UPDATE)
from src.auth.auth_service import AuthUser # For current_user type hint
from src.api.exceptions import handle_api_exceptions, APINotFoundError, APIValidationError
# Assuming core exceptions might be caught by the decorator or service layer
from src.core.exceptions import NotFoundException as CoreNotFoundException
from src.core.exceptions import ServiceException as CoreServiceException

router = APIRouter()

# Dependency function for AnalyticsService (assuming it has a simple constructor or its own Depends)
def get_analytics_service_dependency() -> AnalyticsService:
    # This might need to be more complex if AnalyticsService has its own dependencies
    # that are not auto-wired or available globally.
    # For now, assume a simple instantiation or that FastAPI handles its deps.
    # Based on previous files, services are often instantiated directly.
    return AnalyticsService()

# Dependency function for ClientPreferenceService
def get_client_preference_service_dependency() -> ClientPreferenceService:
    # Similar assumption as AnalyticsService
    return ClientPreferenceService()

# Dependency function for SuggestionService
def get_suggestion_service(
    analytics_service: AnalyticsService = Depends(get_analytics_service_dependency),
    client_preference_service: ClientPreferenceService = Depends(get_client_preference_service_dependency)
) -> SuggestionService:
    return SuggestionService(
        analytics_service=analytics_service,
        client_preference_service=client_preference_service
    )

# --- Request Models ---
class ActionPlanStepStatusUpdate(BaseModel):
    new_status: str


# --- API Endpoints ---

@router.get(
    "/client/{client_id}",
    response_model=List[SuggestionWithActionPlan],
    summary="Get Suggestions for a Client",
    description="Generates and retrieves a list of suggestions with action plans for a given client ID based on their preferences and analytics data.",
    dependencies=[Depends(require_permission(Permission.SUGGESTION_READ))]
)
@handle_api_exceptions("Get Client Suggestions")
async def get_suggestions_for_client(
    client_id: str = Path(..., description="The ID of the client for whom to generate suggestions."),
    days: Optional[int] = Query(30, description="Analysis period in days for generating suggestions.", ge=1, le=365),
    suggestion_service: SuggestionService = Depends(get_suggestion_service),
    current_user: AuthUser = Depends(get_current_active_user) # Ensure user is authenticated
):
    suggestions = await suggestion_service.generate_suggestions(client_id=client_id, days=days)
    if not suggestions:
        # Depending on desired behavior, could return 200 with empty list or 404 if client_id itself is invalid
        # The service currently returns [] if prefs not found or analytics error.
        # If client_id was invalid leading to no prefs, service might raise CoreNotFoundException.
        # For now, an empty list is a valid response.
        pass
    return suggestions

@router.get(
    "/{suggestion_id}",
    response_model=SuggestionWithActionPlan, # Optional handled by APINotFoundError
    summary="Get Suggestion Details",
    description="Retrieves the details of a specific suggestion, including its action plan, by suggestion ID.",
    dependencies=[Depends(require_permission(Permission.SUGGESTION_READ))]
)
@handle_api_exceptions("Get Suggestion Details")
async def get_suggestion_details(
    suggestion_id: str = Path(..., description="The unique identifier for the suggestion."),
    suggestion_service: SuggestionService = Depends(get_suggestion_service),
    current_user: AuthUser = Depends(get_current_active_user)
):
    suggestion_detail = await suggestion_service.get_suggestion_details(suggestion_id=suggestion_id)
    if not suggestion_detail:
        raise APINotFoundError(f"Suggestion with ID '{suggestion_id}' not found.")
    return suggestion_detail

@router.put(
    "/action-plans/{action_plan_id}/steps/{step_id}/status",
    response_model=ActionPlan, # Optional handled by APINotFoundError
    summary="Update Action Plan Step Status",
    description="Updates the status of a specific step within a given action plan.",
    dependencies=[Depends(require_permission(Permission.ACTION_PLAN_UPDATE))]
)
@handle_api_exceptions("Update Action Plan Step Status")
async def update_action_plan_step_status(
    action_plan_id: str = Path(..., description="The unique identifier for the action plan."),
    step_id: str = Path(..., description="The unique identifier for the action plan step."),
    status_update: ActionPlanStepStatusUpdate = Body(...),
    suggestion_service: SuggestionService = Depends(get_suggestion_service),
    current_user: AuthUser = Depends(get_current_active_user)
):
    # Basic validation for new_status if needed, though Pydantic model might handle some
    if not status_update.new_status.strip():
        raise APIValidationError("New status cannot be empty.")

    updated_action_plan = await suggestion_service.update_action_plan_step_status(
        action_plan_id=action_plan_id,
        step_id=step_id,
        new_status=status_update.new_status
    )
    if not updated_action_plan:
        raise APINotFoundError(f"Action plan with ID '{action_plan_id}' or step ID '{step_id}' not found, or update failed.")
    return updated_action_plan
