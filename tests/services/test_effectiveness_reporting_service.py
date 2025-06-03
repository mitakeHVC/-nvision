import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.effectiveness_reporting_service import EffectivenessReportingService
from src.services.analytics_service import AnalyticsService
from src.repositories.suggestion_repository import SuggestionRepository
from src.data_models.reporting_models import EffectivenessReport, MetricValue
from src.data_models.suggestion_models import ActionPlan # For mock return from repo
from src.core.exceptions import NotFoundException

@pytest_asyncio.fixture
async def mock_analytics_service():
    service = MagicMock(spec=AnalyticsService)
    service.get_comprehensive_dashboard = AsyncMock()
    # Add other methods if generate_report_for_action_plan evolves to use them
    return service

@pytest_asyncio.fixture
async def mock_suggestion_repository():
    repo = MagicMock(spec=SuggestionRepository)
    repo.get_action_plan_by_id = AsyncMock()
    return repo

@pytest_asyncio.fixture
async def reporting_service(mock_analytics_service, mock_suggestion_repository):
    return EffectivenessReportingService(
        analytics_service=mock_analytics_service,
        suggestion_repository=mock_suggestion_repository
    )

@pytest.mark.asyncio
async def test_generate_report_action_plan_not_found(reporting_service: EffectivenessReportingService, mock_suggestion_repository: MagicMock):
    mock_suggestion_repository.get_action_plan_by_id.return_value = None
    action_plan_id = str(uuid.uuid4())

    with pytest.raises(NotFoundException, match=f"ActionPlan with id {action_plan_id} not found."):
        await reporting_service.generate_report_for_action_plan(
            action_plan_id=action_plan_id,
            reporting_period_start=datetime(2023, 1, 1),
            reporting_period_end=datetime(2023, 1, 31)
        )

@pytest.mark.asyncio
async def test_generate_report_cannot_determine_target_entity(reporting_service: EffectivenessReportingService, mock_suggestion_repository: MagicMock):
    action_plan_id = str(uuid.uuid4())
    mock_action_plan = ActionPlan(id=action_plan_id, suggestion_id=str(uuid.uuid4()), title="Generic Action Plan", overview="...")
    mock_suggestion_repository.get_action_plan_by_id.return_value = mock_action_plan

    report = await reporting_service.generate_report_for_action_plan(
        action_plan_id=action_plan_id,
        reporting_period_start=datetime(2023, 1, 1),
        reporting_period_end=datetime(2023, 1, 31)
    )

    assert report is not None
    assert "Could not automatically determine target entity" in report.summary
    assert len(report.key_metrics) == 0

@pytest.mark.asyncio
async def test_generate_report_success_with_product_metrics(
    reporting_service: EffectivenessReportingService,
    mock_suggestion_repository: MagicMock,
    mock_analytics_service: MagicMock
):
    action_plan_id = str(uuid.uuid4())
    product_name = "SuperWidget"
    mock_action_plan = ActionPlan(
        id=action_plan_id,
        suggestion_id=str(uuid.uuid4()),
        title=f"Action Plan for Product: {product_name}", # Title implies product
        overview="Improve SuperWidget sales."
    )
    mock_suggestion_repository.get_action_plan_by_id.return_value = mock_action_plan

    # Mock analytics data for reporting period
    reporting_product_data = [
        {"product_name": product_name, "total_revenue": 1500, "units_sold": 150},
        {"product_name": "OtherWidget", "total_revenue": 500, "units_sold": 50},
    ]
    # Mock analytics data for baseline period
    baseline_product_data = [
        {"product_name": product_name, "total_revenue": 1000, "units_sold": 100},
        {"product_name": "OtherWidget", "total_revenue": 600, "units_sold": 60},
    ]

    # Configure side_effect for get_comprehensive_dashboard
    # It will be called for reporting period first, then baseline period
    mock_analytics_service.get_comprehensive_dashboard.side_effect = [
        {"product_analytics": {"products_data": reporting_product_data}}, # Reporting call
        {"product_analytics": {"products_data": baseline_product_data}},  # Baseline call
    ]

    report_start = datetime(2023, 2, 1)
    report_end = datetime(2023, 2, 28)
    baseline_start = datetime(2023, 1, 1)
    baseline_end = datetime(2023, 1, 31)

    report = await reporting_service.generate_report_for_action_plan(
        action_plan_id=action_plan_id,
        reporting_period_start=report_start,
        reporting_period_end=report_end,
        baseline_period_start=baseline_start,
        baseline_period_end=baseline_end,
        generated_by="test_user"
    )

    assert report is not None
    assert report.action_plan_id == action_plan_id
    assert report.action_plan_title == mock_action_plan.title
    assert report.generated_by == "test_user"
    assert len(report.key_metrics) == 2

    revenue_metric = next(m for m in report.key_metrics if m.metric_name == f"Sales Revenue ({product_name})")
    assert revenue_metric.value == 1500
    assert revenue_metric.change_from_baseline == 50.0 # (1500-1000)/1000 * 100

    units_metric = next(m for m in report.key_metrics if m.metric_name == f"Units Sold ({product_name})")
    assert units_metric.value == 150
    assert units_metric.change_from_baseline == 50.0 # (150-100)/100 * 100

    assert f"Reporting period revenue: 1500 USD. Baseline: 1000 USD. Change: 50.0%." in report.summary
    assert f"Reporting period units sold: 150. Baseline: 100. Change: 50.0%." in report.summary

    assert mock_analytics_service.get_comprehensive_dashboard.call_count == 2


@pytest.mark.asyncio
async def test_generate_report_no_baseline_data(
    reporting_service: EffectivenessReportingService,
    mock_suggestion_repository: MagicMock,
    mock_analytics_service: MagicMock
):
    action_plan_id = str(uuid.uuid4())
    product_name = "SoloWidget"
    mock_action_plan = ActionPlan(id=action_plan_id, suggestion_id=str(uuid.uuid4()), title=f"Action Plan for: {product_name}", overview="...")
    mock_suggestion_repository.get_action_plan_by_id.return_value = mock_action_plan

    reporting_product_data = [{"product_name": product_name, "total_revenue": 1200, "units_sold": 120}]
    mock_analytics_service.get_comprehensive_dashboard.return_value = {
        "product_analytics": {"products_data": reporting_product_data}
    } # Only one call, for reporting period

    report = await reporting_service.generate_report_for_action_plan(
        action_plan_id=action_plan_id,
        reporting_period_start=datetime(2023, 2, 1),
        reporting_period_end=datetime(2023, 2, 28)
        # No baseline period provided
    )
    assert report is not None
    assert len(report.key_metrics) == 2
    revenue_metric = next(m for m in report.key_metrics if "Revenue" in m.metric_name)
    assert revenue_metric.value == 1200
    assert revenue_metric.change_from_baseline is None
    assert "Reporting period revenue: 1200 USD." in report.summary
    mock_analytics_service.get_comprehensive_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_product_not_in_analytics(
    reporting_service: EffectivenessReportingService,
    mock_suggestion_repository: MagicMock,
    mock_analytics_service: MagicMock
):
    action_plan_id = str(uuid.uuid4())
    product_name = "GhostWidget"
    mock_action_plan = ActionPlan(id=action_plan_id, suggestion_id=str(uuid.uuid4()), title=f"Action Plan for Product: {product_name}", overview="...")
    mock_suggestion_repository.get_action_plan_by_id.return_value = mock_action_plan

    # Product "GhostWidget" is not in the analytics data
    reporting_product_data = [{"product_name": "OtherWidget", "total_revenue": 500, "units_sold": 50}]
    mock_analytics_service.get_comprehensive_dashboard.return_value = {
        "product_analytics": {"products_data": reporting_product_data}
    }

    report = await reporting_service.generate_report_for_action_plan(
        action_plan_id=action_plan_id,
        reporting_period_start=datetime(2023, 2, 1),
        reporting_period_end=datetime(2023, 2, 28)
    )
    assert report is not None
    assert len(report.key_metrics) == 0
    assert f"No specific product metrics found for '{product_name}'" in report.summary


# Placeholder tests for other service methods
@pytest.mark.asyncio
async def test_get_report_by_id_placeholder(reporting_service: EffectivenessReportingService):
    report = await reporting_service.get_report_by_id("existing_report_uuid_xyz")
    assert report is not None
    assert report.id == "existing_report_uuid_xyz"
    report_not_found = await reporting_service.get_report_by_id("non_existent_id")
    assert report_not_found is None

@pytest.mark.asyncio
async def test_list_reports_for_action_plan_placeholder(reporting_service: EffectivenessReportingService):
    reports = await reporting_service.list_reports_for_action_plan("existing_plan_for_report_abc")
    assert len(reports) == 1
    assert reports[0].action_plan_id == "existing_plan_for_report_abc"

    no_reports = await reporting_service.list_reports_for_action_plan("plan_with_no_reports")
    assert len(no_reports) == 0
