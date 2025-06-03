from typing import List, Optional, Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException, status
from pydantic import BaseModel

from src.services.effectiveness_reporting_service import EffectivenessReportingService
from src.services.analytics_service import AnalyticsService # For DI
from src.repositories.suggestion_repository import SuggestionRepository # For DI
from src.data_models.reporting_models import EffectivenessReport
from src.auth.dependencies import get_current_active_user, require_permission
from src.auth.permissions import Permission # Will add REPORT_READ
from src.auth.auth_service import AuthUser # For current_user type hint
from src.api.exceptions import handle_api_exceptions, APINotFoundError, APIValidationError
from src.core.exceptions import NotFoundException as CoreNotFoundException

router = APIRouter()

# --- Dependency Injection Setup ---

# Assuming these dependency functions for AnalyticsService and SuggestionRepository
# are similar to what was set up for SuggestionService's dependencies.
# If they are already defined globally or in another common place, they could be imported.

def get_analytics_service_dependency() -> AnalyticsService:
    # Placeholder: Assumes simple instantiation or existing global/DI setup for AnalyticsService
    # This might need to be more complex if AnalyticsService has its own dependencies.
    return AnalyticsService()

def get_suggestion_repository_dependency() -> SuggestionRepository:
    # Placeholder: Assumes Neo4jConnector is available or AnalyticsService has simple init.
    # This might require Neo4jConnector to be injectable if not globally available.
    from src.neo4j_utils.connector import Neo4jConnector
    connector = Neo4jConnector() # This line might be problematic if Neo4jConnector needs config
    return SuggestionRepository(neo4j_connector=connector)

def get_effectiveness_reporting_service(
    analytics_service: AnalyticsService = Depends(get_analytics_service_dependency),
    suggestion_repository: SuggestionRepository = Depends(get_suggestion_repository_dependency)
) -> EffectivenessReportingService:
    return EffectivenessReportingService(
        analytics_service=analytics_service,
        suggestion_repository=suggestion_repository
    )

# --- Request Models ---

class ReportGenerationRequest(BaseModel):
    reporting_period_start: datetime
    reporting_period_end: datetime
    baseline_period_start: Optional[datetime] = None
    baseline_period_end: Optional[datetime] = None


# --- API Endpoints ---

@router.post(
    "/effectiveness/action-plan/{action_plan_id}",
    response_model=EffectivenessReport, # Optional handled by APINotFoundError or decorator
    summary="Generate Effectiveness Report for an Action Plan",
    description="Triggers the generation of an effectiveness report for a specific action plan over a defined period.",
    status_code=status.HTTP_201_CREATED, # 201 for successful creation/generation of a new resource
    dependencies=[Depends(require_permission(Permission.REPORT_READ))]
)
@handle_api_exceptions("Generate Effectiveness Report")
async def generate_effectiveness_report(
    action_plan_id: str = Path(..., description="The ID of the action plan to evaluate."),
    request_body: ReportGenerationRequest = Body(...),
    service: EffectivenessReportingService = Depends(get_effectiveness_reporting_service),
    current_user: AuthUser = Depends(get_current_active_user)
) -> EffectivenessReport:
    report = await service.generate_report_for_action_plan(
        action_plan_id=action_plan_id,
        reporting_period_start=request_body.reporting_period_start,
        reporting_period_end=request_body.reporting_period_end,
        baseline_period_start=request_body.baseline_period_start,
        baseline_period_end=request_body.baseline_period_end,
        generated_by=str(current_user.user_id)
    )
    if not report: # Should be handled by service raising CoreNotFoundException if action plan not found
        raise APINotFoundError(f"Could not generate report or ActionPlan with ID '{action_plan_id}' not found.")
    return report

@router.get(
    "/effectiveness/{report_id}",
    response_model=EffectivenessReport, # Optional handled by APINotFoundError
    summary="Get Specific Effectiveness Report",
    description="Retrieves an effectiveness report by its unique ID.",
    dependencies=[Depends(require_permission(Permission.REPORT_READ))]
)
@handle_api_exceptions("Get Effectiveness Report by ID")
async def get_effectiveness_report_by_id(
    report_id: str = Path(..., description="The unique ID of the report to retrieve."),
    service: EffectivenessReportingService = Depends(get_effectiveness_reporting_service),
    current_user: AuthUser = Depends(get_current_active_user)
) -> EffectivenessReport:
    report = await service.get_report_by_id(report_id=report_id)
    if not report:
        raise APINotFoundError(f"EffectivenessReport with ID '{report_id}' not found.")
    return report

@router.get(
    "/effectiveness/action-plan/{action_plan_id}/list",
    response_model=List[EffectivenessReport],
    summary="List Reports for an Action Plan",
    description="Retrieves a list of all effectiveness reports generated for a specific action plan.",
    dependencies=[Depends(require_permission(Permission.REPORT_READ))]
)
@handle_api_exceptions("List Reports for Action Plan")
async def list_reports_for_action_plan(
    action_plan_id: str = Path(..., description="The ID of the action plan whose reports are to be listed."),
    service: EffectivenessReportingService = Depends(get_effectiveness_reporting_service),
    current_user: AuthUser = Depends(get_current_active_user)
) -> List[EffectivenessReport]:
    reports = await service.list_reports_for_action_plan(action_plan_id=action_plan_id)
    # An empty list is a valid response if no reports exist, so no explicit check for empty here.
    return reports
