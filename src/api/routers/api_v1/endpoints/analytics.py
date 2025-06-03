from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_active_user, require_permission
from src.auth.permissions import Permission
from src.services.analytics_service import AnalyticsService
from src.api.exceptions import handle_api_exceptions # Import the decorator

router = APIRouter()


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


@router.get(
    "/dashboard",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
@handle_api_exceptions("Get Comprehensive Dashboard")
async def get_comprehensive_dashboard(
    days: Optional[int] = Query(30, description="Analysis period in days"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Retrieve comprehensive dashboard analytics.
    """
    return await analytics_service.get_comprehensive_dashboard(days=days)


@router.get(
    "/sales",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
@handle_api_exceptions("Get Sales Analytics")
async def get_sales_analytics(
    days: Optional[int] = Query(30, description="Analysis period in days"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Retrieve sales analytics.
    """
    return await analytics_service.get_sales_analytics(days=days)


@router.get(
    "/customers",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
@handle_api_exceptions("Get Customer Analytics")
async def get_customer_analytics(
    days: Optional[int] = Query(30, description="Analysis period in days"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Retrieve customer analytics.
    """
    return await analytics_service.get_customer_analytics(days=days)


@router.get(
    "/products",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
@handle_api_exceptions("Get Product Analytics")
async def get_product_analytics(
    days: Optional[int] = Query(30, description="Analysis period in days"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Retrieve product analytics.
    """
    return await analytics_service.get_product_analytics(days=days)


@router.get(
    "/crm",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission(Permission.ANALYTICS_READ))],
)
@handle_api_exceptions("Get CRM Analytics")
async def get_crm_analytics(
    days: Optional[int] = Query(30, description="Analysis period in days"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Retrieve CRM analytics.
    """
    return await analytics_service.get_crm_analytics(days=days)
