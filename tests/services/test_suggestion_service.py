import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.suggestion_service import SuggestionService
from src.services.analytics_service import AnalyticsService
from src.services.client_preference_service import ClientPreferenceService
from src.data_models.suggestion_models import Suggestion, ActionPlan, ActionPlanStep, SuggestionWithActionPlan # Added ActionPlanStep
from src.data_models.client_preferences_models import ClientPreference # For mock return
from src.core.exceptions import ServiceException, NotFoundException
from src.repositories.suggestion_repository import SuggestionRepository


@pytest_asyncio.fixture
async def mock_analytics_service():
    service = MagicMock(spec=AnalyticsService)
    service.get_comprehensive_dashboard = AsyncMock()
    return service

@pytest_asyncio.fixture
async def mock_client_preference_service():
    service = MagicMock(spec=ClientPreferenceService)
    service.get_preferences_by_client_id = AsyncMock()
    return service

@pytest_asyncio.fixture
async def mock_suggestion_repository():
    repo = MagicMock(spec=SuggestionRepository)
    repo.save_suggestion_with_plan = AsyncMock()
    repo.get_suggestion_with_plan_by_id = AsyncMock()
    repo.get_action_plan_by_id = AsyncMock()
    repo.update_action_plan = AsyncMock()
    return repo

@pytest_asyncio.fixture
async def suggestion_service(mock_analytics_service, mock_client_preference_service, mock_suggestion_repository):
    return SuggestionService(
        analytics_service=mock_analytics_service,
        client_preference_service=mock_client_preference_service,
        suggestion_repository=mock_suggestion_repository # Inject mock repository
    )

@pytest.mark.asyncio
async def test_generate_suggestions_no_preferences(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock):
    mock_client_preference_service.get_preferences_by_client_id.return_value = None
    client_id = str(uuid.uuid4())

    # It currently prints a warning and proceeds, rules then check prefs.
    # If no rules match due to no relevant prefs, it will be an empty list.
    suggestions = await suggestion_service.generate_suggestions(client_id=client_id)

    assert suggestions == []
    mock_client_preference_service.get_preferences_by_client_id.assert_called_once_with(client_id)

@pytest.mark.asyncio
async def test_generate_suggestions_analytics_error(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock, mock_analytics_service: MagicMock):
    client_id = str(uuid.uuid4())
    mock_client_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=str(uuid.uuid4()), client_id=client_id, preferences_payload={"target_areas": ["inventory_optimization"]}
    )
    mock_analytics_service.get_comprehensive_dashboard.side_effect = Exception("Analytics service error")

    # The service currently catches Exception and returns [], logging an error.
    suggestions = await suggestion_service.generate_suggestions(client_id=client_id)
    assert suggestions == []
    # The service currently catches Exception and returns [], logging an error.
    # For a more robust test, we might want to assert that a specific type of error was logged
    # or that the service re-raises a specific ServiceException.
    # For now, asserting empty list based on current implementation.
    # The call was duplicated, removing one.
    assert suggestions == []
    mock_analytics_service.get_comprehensive_dashboard.assert_called_once_with(days=30)


@pytest.mark.asyncio
async def test_generate_suggestions_no_analytics_data(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock, mock_analytics_service: MagicMock):
    client_id = str(uuid.uuid4())
    mock_client_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=str(uuid.uuid4()), client_id=client_id, preferences_payload={"target_areas": ["inventory_optimization"]}
    )
    mock_analytics_service.get_comprehensive_dashboard.return_value = None # No data

    suggestions = await suggestion_service.generate_suggestions(client_id=client_id)
    assert suggestions == []

@pytest.mark.asyncio
async def test_product_inventory_mismatch_rule_triggers(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock, mock_analytics_service: MagicMock):
    client_id = str(uuid.uuid4())
    mock_client_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=str(uuid.uuid4()),
        client_id=client_id,
        preferences_payload={"target_areas": ["inventory_optimization", "sales_improvement"]}
    )

    product_data = [
        {"product_id": "P001", "product_name": "Laptop X", "total_revenue": 100, "stock_quantity": 60},
        {"product_id": "P002", "product_name": "Mouse Y", "total_revenue": 50, "stock_quantity": 70},
        {"product_id": "P003", "product_name": "Keyboard Z", "total_revenue": 1000, "stock_quantity": 10},
        {"product_id": "P004", "product_name": "Monitor A", "total_revenue": 2000, "stock_quantity": 5},
        {"product_id": "P005", "product_name": "Webcam B", "total_revenue": 30, "stock_quantity": 60}, # Low sales (lowest), high stock
        {"product_id": "P006", "product_name": "Dock C", "total_revenue": 150, "stock_quantity": 100},
    ]
    # Sorted by revenue: P005 (30), P002 (50), P001 (100), P006 (150), P003 (1000), P004 (2000)
    # Bottom 20% of 6 products = 1 product: P005 (Webcam B)
    # P005 has stock 60, which is > high_inventory_threshold (50). So P005 should trigger.

    mock_analytics_service.get_comprehensive_dashboard.return_value = {
        "product_analytics": {"products_data": product_data}
    }

    suggestions = await suggestion_service.generate_suggestions(client_id=client_id)

    assert len(suggestions) == 1
    suggestion_with_plan = suggestions[0]
    assert suggestion_with_plan.suggestion.title == "Review Low-Performing Product: Webcam B" # Corrected expected product
    assert "low sales (revenue: 30)" in suggestion_with_plan.suggestion.description
    assert "high inventory (60 units)" in suggestion_with_plan.suggestion.description
    assert suggestion_with_plan.suggestion.source_analysis_type == "product_inventory_sales_mismatch"
    assert len(suggestion_with_plan.action_plan.steps) == 2

    # Verify save_suggestion_with_plan was called
    mock_suggestion_repository = suggestion_service.suggestion_repository
    mock_suggestion_repository.save_suggestion_with_plan.assert_called_once_with(
        suggestion_with_plan, # The generated item
        created_by_user_id=client_id # Match keyword argument
    )

@pytest.mark.asyncio
async def test_product_inventory_mismatch_rule_no_trigger_due_to_prefs(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock, mock_analytics_service: MagicMock, mock_suggestion_repository: MagicMock):
    client_id = str(uuid.uuid4())
    mock_client_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=str(uuid.uuid4()),
        client_id=client_id,
        preferences_payload={"target_areas": ["customer_engagement"]} # Not interested in inventory/sales
    )
    # Same product data as above, which would trigger if prefs matched
    product_data = [{"product_id": "P002", "product_name": "Mouse Y", "total_revenue": 50, "stock_quantity": 70}]
    mock_analytics_service.get_comprehensive_dashboard.return_value = {
        "product_analytics": {"products_data": product_data}
    }

    suggestions = await suggestion_service.generate_suggestions(client_id=client_id)
    assert len(suggestions) == 0
    mock_suggestion_repository.save_suggestion_with_plan.assert_not_called()

@pytest.mark.asyncio
async def test_product_inventory_mismatch_rule_no_trigger_no_low_sales_high_stock(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock, mock_analytics_service: MagicMock, mock_suggestion_repository: MagicMock):
    client_id = str(uuid.uuid4())
    mock_client_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=str(uuid.uuid4()),
        client_id=client_id,
        preferences_payload={"target_areas": ["inventory_optimization"]}
    )
    # Product data where no product meets both low sales AND high stock criteria
    product_data = [
        {"product_id": "P001", "product_name": "Laptop X", "total_revenue": 100, "stock_quantity": 10}, # Low sales, low stock
        {"product_id": "P003", "product_name": "Keyboard Z", "total_revenue": 1000, "stock_quantity": 60}, # High sales, high stock
    ]
    mock_analytics_service.get_comprehensive_dashboard.return_value = {
        "product_analytics": {"products_data": product_data}
    }

    suggestions = await suggestion_service.generate_suggestions(client_id=client_id)
    assert len(suggestions) == 0
    mock_suggestion_repository.save_suggestion_with_plan.assert_not_called()

@pytest.mark.asyncio
async def test_product_inventory_mismatch_rule_handles_missing_product_analytics_data(suggestion_service: SuggestionService, mock_client_preference_service: MagicMock, mock_analytics_service: MagicMock, mock_suggestion_repository: MagicMock):
    client_id = str(uuid.uuid4())
    mock_client_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=str(uuid.uuid4()),
        client_id=client_id,
        preferences_payload={"target_areas": ["inventory_optimization"]}
    )
    # Analytics data missing 'product_analytics' or 'products_data'
    mock_analytics_service.get_comprehensive_dashboard.return_value = {"some_other_analytics": {}}
    suggestions1 = await suggestion_service.generate_suggestions(client_id=client_id)
    assert len(suggestions1) == 0

    mock_analytics_service.get_comprehensive_dashboard.return_value = {"product_analytics": {"products_data": []}} # Empty list
    suggestions2 = await suggestion_service.generate_suggestions(client_id=client_id)
    assert len(suggestions2) == 0

    mock_analytics_service.get_comprehensive_dashboard.return_value = {"product_analytics": None} # product_analytics is None
    suggestions3 = await suggestion_service.generate_suggestions(client_id=client_id)
    assert len(suggestions3) == 0

# Tests for placeholder methods (get_suggestion_details, update_action_plan_step_status)
@pytest.mark.asyncio
async def test_get_suggestion_details_placeholder(suggestion_service: SuggestionService, mock_suggestion_repository: MagicMock):
    test_suggestion_id = "existing_suggestion_uuid_123"
    # Mock what the repository returns
    mock_suggestion = Suggestion(id=test_suggestion_id, title="Test", description="Test", source_analysis_type="test")
    mock_return_val = SuggestionWithActionPlan(suggestion=mock_suggestion) # Can add action_plan if needed
    mock_suggestion_repository.get_suggestion_with_plan_by_id.return_value = mock_return_val

    details = await suggestion_service.get_suggestion_details(test_suggestion_id)
    assert details is not None
    assert details.suggestion.id == test_suggestion_id
    mock_suggestion_repository.get_suggestion_with_plan_by_id.assert_called_once_with(test_suggestion_id)

    # Test with a random UUID for not found case
    random_id = str(uuid.uuid4())
    mock_suggestion_repository.get_suggestion_with_plan_by_id.return_value = None # Simulate not found
    details_random = await suggestion_service.get_suggestion_details(random_id)
    assert details_random is None

@pytest.mark.asyncio
async def test_update_action_plan_step_status_placeholder(suggestion_service: SuggestionService, mock_suggestion_repository: MagicMock):
    action_plan_id = "existing_action_plan_uuid_abc"
    step_id_to_update = "step1_uuid" # Using a step_id that could exist in a dummy plan
    new_status = "completed"
    user_id = "test_updater"

    # Mock get_action_plan_by_id
    dummy_suggestion_id = str(uuid.uuid4())
    original_action_plan = ActionPlan(
        id=action_plan_id,
        suggestion_id=dummy_suggestion_id,
        title="Sample Action Plan",
        overview="Overview",
        steps=[
            ActionPlanStep(step_id="step1_uuid", description="Initial step", status="pending"),
            ActionPlanStep(step_id="step2_uuid", description="Another step", status="pending")
        ]
    )
    mock_suggestion_repository.get_action_plan_by_id.return_value = original_action_plan

    # Mock update_action_plan to return the plan it receives (or a modified version)
    async def mock_update(plan, updater_id):
        # This mock should reflect that the step status and plan's updated_at/overall_status are changed
        # The service logic will modify 'plan' in place before passing to this mock.
        return plan
    mock_suggestion_repository.update_action_plan.side_effect = mock_update

    updated_plan = await suggestion_service.update_action_plan_step_status(
        action_plan_id, step_id_to_update, new_status, updated_by_user_id=user_id
    )

    assert updated_plan is not None
    assert updated_plan.id == action_plan_id
    updated_step_found = False
    for step in updated_plan.steps:
        if step.step_id == step_id_to_update:
            assert step.status == "completed"
            updated_step_found = True
            break
    # This assertion will fail if the placeholder doesn't actually find/update the step
    # The current placeholder logic *will* update if action_plan_id matches.
    # Let's refine the placeholder in service to make this test more robust or fix the test.
    # The placeholder service method actually creates a new plan and updates a step if its id matches.
    # So, if step_id_to_update is one of the steps in the dummy plan, it should work.
    # The placeholder service is:
    # ActionPlanStep(step_id=step_id, description="Step to be updated", status="pending"),
    # This means it uses the step_id we pass in, if the action_plan_id matches.

    assert updated_step_found # This will pass if the mock service correctly "updates" the step by ID.
                               # The placeholder in service is:
                               # ActionPlanStep(step_id=step_id, description="Step to be updated", status="pending")
                               # This means it uses the step_id we pass in.

    # Test with a non-existent step_id (assuming placeholder returns None if step not found)
    non_existent_step_id = str(uuid.uuid4())
    # The service method update_action_plan_step_status expects updated_by_user_id
    # It should raise NotFoundException if step_id is not found.
    with pytest.raises(NotFoundException):
        await suggestion_service.update_action_plan_step_status(
            action_plan_id, non_existent_step_id, "completed", updated_by_user_id=user_id
        )
    # The current placeholder will actually ADD this step with new status if action_plan_id matches,
    # then find it. This isn't ideal placeholder logic.
    # For this test, we assume the placeholder might return None or raise if step_id not in its *predefined* dummy steps.
    # The placeholder creates `ActionPlanStep(step_id=step_id, ...)` using the passed step_id.
    # So, it will always "find" the step to update.
    # A better placeholder would have fixed step_ids and return None if step_id not found.
    # Given the current placeholder, this part of the test is less meaningful for "not found step".
    # assert plan_for_non_existent_step is None

    # Test with a non-existent action_plan_id
    non_existent_action_plan_id = str(uuid.uuid4())
    plan_for_non_existent_action = await suggestion_service.update_action_plan_step_status(non_existent_action_plan_id, step_id_to_update, "completed")
    assert plan_for_non_existent_action is None

# Note: The placeholder tests are highly dependent on the hardcoded logic in the service's placeholders.
# They will need significant updates when the actual service logic is implemented.
