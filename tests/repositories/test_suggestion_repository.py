import pytest
import pytest_asyncio
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.repositories.suggestion_repository import SuggestionRepository
from src.data_models.suggestion_models import Suggestion, ActionPlan, ActionPlanStep, SuggestionWithActionPlan
from src.neo4j_utils.connector import Neo4jConnector
from src.core.exceptions import DatabaseException, NotFoundException


@pytest.fixture
def mock_neo4j_connector():
    connector = MagicMock(spec=Neo4jConnector)
    connector.execute_query = AsyncMock()
    return connector

@pytest.fixture
def suggestion_repository(mock_neo4j_connector):
    with patch.object(SuggestionRepository, '_ensure_constraints', return_value=None):
        repo = SuggestionRepository(neo4j_connector=mock_neo4j_connector)
    return repo

@pytest_asyncio.fixture
async def sample_suggestion_id():
    return str(uuid.uuid4())

@pytest_asyncio.fixture
async def sample_action_plan_id():
    return str(uuid.uuid4())

@pytest_asyncio.fixture
async def sample_suggestion(sample_suggestion_id):
    return Suggestion(
        id=sample_suggestion_id,
        title="Test Suggestion",
        description="A test suggestion description.",
        source_analysis_type="test_analysis",
        severity="medium",
        related_data_points=[{"key": "value"}],
        potential_impact="High",
        created_at=datetime.now(timezone.utc)
        # created_by_user_id will be passed to save method
    )

@pytest_asyncio.fixture
async def sample_action_plan(sample_action_plan_id, sample_suggestion_id):
    return ActionPlan(
        id=sample_action_plan_id,
        suggestion_id=sample_suggestion_id,
        title="Test Action Plan",
        overview="Overview of the test action plan.",
        steps=[
            ActionPlanStep(description="Step 1 for test plan"),
            ActionPlanStep(description="Step 2 for test plan", status="in_progress")
        ],
        overall_status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
        # created_by_user_id and updated_by_user_id will be passed to save/update methods
    )

@pytest_asyncio.fixture
async def sample_suggestion_with_plan(sample_suggestion, sample_action_plan):
    return SuggestionWithActionPlan(suggestion=sample_suggestion, action_plan=sample_action_plan)

@pytest_asyncio.fixture
async def sample_suggestion_without_plan(sample_suggestion):
    return SuggestionWithActionPlan(suggestion=sample_suggestion, action_plan=None)

# --- Test Cases ---

@pytest.mark.asyncio
async def test_save_suggestion_with_plan_full(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_suggestion_with_plan: SuggestionWithActionPlan):
    created_by = "user_test_1"
    # Mock execute_query to return values indicating success (e.g., node data or relationship type)
    mock_neo4j_connector.execute_query.side_effect = [
        [{"s": sample_suggestion_with_plan.suggestion.model_dump()}], # For suggestion MERGE
        [{"ap": sample_suggestion_with_plan.action_plan.model_dump()}], # For action plan MERGE
        [{"type(r)": "HAS_ACTION_PLAN"}] # For relationship MERGE
    ]

    result = await suggestion_repository.save_suggestion_with_plan(sample_suggestion_with_plan, created_by)

    assert result == sample_suggestion_with_plan
    assert mock_neo4j_connector.execute_query.call_count == 3

    # Call 1: Suggestion Node
    args_sugg, _ = mock_neo4j_connector.execute_query.call_args_list[0]
    query_sugg, params_sugg = args_sugg
    assert f"MERGE (s:{SuggestionRepository._suggestion_label} {{id: $suggestion_id}})" in query_sugg
    assert params_sugg["suggestion_id"] == sample_suggestion_with_plan.suggestion.id
    assert params_sugg["suggestion_props"]["created_by_user_id"] == created_by
    assert "related_data_points_json" in params_sugg["suggestion_props"]

    # Call 2: ActionPlan Node
    args_ap, _ = mock_neo4j_connector.execute_query.call_args_list[1]
    query_ap, params_ap = args_ap
    assert f"MERGE (ap:{SuggestionRepository._action_plan_label} {{id: $action_plan_id}})" in query_ap
    assert params_ap["action_plan_id"] == sample_suggestion_with_plan.action_plan.id
    assert params_ap["action_plan_props"]["created_by_user_id"] == created_by
    assert "steps_json" in params_ap["action_plan_props"]

    # Call 3: Relationship
    args_rel, _ = mock_neo4j_connector.execute_query.call_args_list[2]
    query_rel, params_rel = args_rel
    assert f"MATCH (s:{SuggestionRepository._suggestion_label} {{id: $suggestion_id}})" in query_rel
    assert f"MATCH (ap:{SuggestionRepository._action_plan_label} {{id: $action_plan_id}})" in query_rel
    assert f"MERGE (s)-[r:{SuggestionRepository._has_action_plan_rel}]->(ap)" in query_rel
    assert params_rel["suggestion_id"] == sample_suggestion_with_plan.suggestion.id
    assert params_rel["action_plan_id"] == sample_suggestion_with_plan.action_plan.id


@pytest.mark.asyncio
async def test_save_suggestion_without_plan(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_suggestion_without_plan: SuggestionWithActionPlan):
    created_by = "user_test_2"
    mock_neo4j_connector.execute_query.return_value = [{"s": sample_suggestion_without_plan.suggestion.model_dump()}]

    result = await suggestion_repository.save_suggestion_with_plan(sample_suggestion_without_plan, created_by)

    assert result == sample_suggestion_without_plan
    mock_neo4j_connector.execute_query.assert_called_once() # Only suggestion node should be created/merged
    args_sugg, _ = mock_neo4j_connector.execute_query.call_args
    query_sugg, params_sugg = args_sugg
    assert f"MERGE (s:{SuggestionRepository._suggestion_label} {{id: $suggestion_id}})" in query_sugg
    assert params_sugg["suggestion_props"]["created_by_user_id"] == created_by


@pytest.mark.asyncio
async def test_get_suggestion_with_plan_by_id_found_full(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_suggestion_with_plan: SuggestionWithActionPlan):
    s_node = sample_suggestion_with_plan.suggestion.model_dump(mode="json") # Use .model_dump(mode="json") for pydantic v2
    s_node["related_data_points_json"] = json.dumps(s_node.pop("related_data_points"))
    ap_node = sample_suggestion_with_plan.action_plan.model_dump(mode="json")
    ap_node["steps_json"] = json.dumps([step.model_dump() for step in sample_suggestion_with_plan.action_plan.steps])
    ap_node.pop("steps")

    mock_neo4j_connector.execute_query.return_value = [{"s": s_node, "ap": ap_node}]

    result = await suggestion_repository.get_suggestion_with_plan_by_id(sample_suggestion_with_plan.suggestion.id)

    assert result is not None
    assert result.suggestion.id == sample_suggestion_with_plan.suggestion.id
    assert result.action_plan.id == sample_suggestion_with_plan.action_plan.id
    assert len(result.action_plan.steps) == len(sample_suggestion_with_plan.action_plan.steps)
    mock_neo4j_connector.execute_query.assert_called_once_with(
        f"""
        MATCH (s:{SuggestionRepository._suggestion_label} {{id: $suggestion_id}})
        OPTIONAL MATCH (s)-[:{SuggestionRepository._has_action_plan_rel}]->(ap:{SuggestionRepository._action_plan_label})
        RETURN s, ap
        """,
        {"suggestion_id": sample_suggestion_with_plan.suggestion.id}
    )

@pytest.mark.asyncio
async def test_get_suggestion_with_plan_by_id_found_no_plan(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_suggestion: Suggestion):
    s_node = sample_suggestion.model_dump(mode="json")
    s_node["related_data_points_json"] = json.dumps(s_node.pop("related_data_points"))
    mock_neo4j_connector.execute_query.return_value = [{"s": s_node, "ap": None}] # No action plan

    result = await suggestion_repository.get_suggestion_with_plan_by_id(sample_suggestion.id)

    assert result is not None
    assert result.suggestion.id == sample_suggestion.id
    assert result.action_plan is None

@pytest.mark.asyncio
async def test_get_suggestion_with_plan_by_id_not_found(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock):
    non_existent_id = str(uuid.uuid4())
    mock_neo4j_connector.execute_query.return_value = [] # No results

    result = await suggestion_repository.get_suggestion_with_plan_by_id(non_existent_id)
    assert result is None

@pytest.mark.asyncio
async def test_get_action_plan_by_id_found(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_action_plan: ActionPlan):
    ap_node = sample_action_plan.model_dump(mode="json")
    ap_node["steps_json"] = json.dumps([step.model_dump() for step in sample_action_plan.steps])
    ap_node.pop("steps")
    mock_neo4j_connector.execute_query.return_value = [{"ap": ap_node}]

    result = await suggestion_repository.get_action_plan_by_id(sample_action_plan.id)

    assert result is not None
    assert result.id == sample_action_plan.id
    assert len(result.steps) == len(sample_action_plan.steps)
    mock_neo4j_connector.execute_query.assert_called_once()

@pytest.mark.asyncio
async def test_get_action_plan_by_id_not_found(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock):
    non_existent_id = str(uuid.uuid4())
    mock_neo4j_connector.execute_query.return_value = []
    result = await suggestion_repository.get_action_plan_by_id(non_existent_id)
    assert result is None

@pytest.mark.asyncio
async def test_update_action_plan(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_action_plan: ActionPlan):
    updated_by = "user_updater_1"
    sample_action_plan.overview = "Updated overview by test"
    sample_action_plan.steps[0].status = "completed"

    # Prepare mock return data (what the DB would return after update)
    updated_ap_node_data = sample_action_plan.model_dump(mode="json")
    updated_ap_node_data["steps_json"] = json.dumps([step.model_dump() for step in sample_action_plan.steps])
    updated_ap_node_data.pop("steps")
    updated_ap_node_data["updated_by_user_id"] = updated_by # Repo sets this
    updated_ap_node_data["updated_at"] = datetime.now(timezone.utc).isoformat() # Repo sets this

    mock_neo4j_connector.execute_query.return_value = [{"ap": updated_ap_node_data}]

    result = await suggestion_repository.update_action_plan(sample_action_plan, updated_by)

    assert result is not None
    assert result.id == sample_action_plan.id
    assert result.overview == "Updated overview by test"
    assert result.steps[0].status == "completed"
    assert result.updated_by_user_id == updated_by

    mock_neo4j_connector.execute_query.assert_called_once()
    call_args = mock_neo4j_connector.execute_query.call_args
    query_string, params_dict = call_args[0]

    assert f"MATCH (ap:{SuggestionRepository._action_plan_label} {{id: $action_plan_id}})" in query_string
    assert "SET ap.overview = $overview" in query_string
    assert "ap.steps_json = $steps_json" in query_string
    assert "ap.updated_by_user_id = $updated_by_user_id" in query_string
    assert params_dict["action_plan_id"] == sample_action_plan.id
    assert params_dict["overview"] == "Updated overview by test"

@pytest.mark.asyncio
async def test_update_action_plan_not_found(suggestion_repository: SuggestionRepository, mock_neo4j_connector: MagicMock, sample_action_plan: ActionPlan):
    updated_by = "user_updater_2"
    mock_neo4j_connector.execute_query.return_value = [] # Simulate not found

    with pytest.raises(NotFoundException): # Repository's update method raises NotFoundException
        await suggestion_repository.update_action_plan(sample_action_plan, updated_by)

    mock_neo4j_connector.execute_query.assert_called_once()
