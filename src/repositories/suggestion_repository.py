import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from src.data_models.suggestion_models import Suggestion, ActionPlan, ActionPlanStep, SuggestionWithActionPlan
from src.neo4j_utils.connector import Neo4jConnector
from src.core.exceptions import DatabaseException, NotFoundException

class SuggestionRepository:
    _suggestion_label = "Suggestion"
    _action_plan_label = "ActionPlan"
    _has_action_plan_rel = "HAS_ACTION_PLAN"

    def __init__(self, neo4j_connector: Neo4jConnector):
        self.db = neo4j_connector
        # Constraints can be added here if needed, e.g., for suggestion_id uniqueness
        # self._ensure_constraints()

    def _ensure_constraints(self):
        try:
            self.db.execute_query(f"CREATE CONSTRAINT IF NOT EXISTS FOR (s:{self._suggestion_label}) REQUIRE s.id IS UNIQUE")
            self.db.execute_query(f"CREATE CONSTRAINT IF NOT EXISTS FOR (ap:{self._action_plan_label}) REQUIRE ap.id IS UNIQUE")
        except Exception as e:
            print(f"Warning: Could not ensure constraints for Suggestion/ActionPlan: {e}")

    async def save_suggestion_with_plan(self, data: SuggestionWithActionPlan, created_by_user_id: str) -> SuggestionWithActionPlan:
        suggestion_props = data.suggestion.model_dump()
        suggestion_props["created_by_user_id"] = created_by_user_id
        # Ensure datetime objects are stored in a consistent format (ISO 8601 string)
        suggestion_props["created_at"] = data.suggestion.created_at.isoformat()
        if data.suggestion.related_data_points is not None:
             suggestion_props["related_data_points_json"] = json.dumps(data.suggestion.related_data_points)
        else:
            suggestion_props["related_data_points_json"] = None # Or an empty list/JSON array string '[]'
        # Remove original list of dicts if we're storing JSON string to avoid Neo4j type issues
        if "related_data_points" in suggestion_props:
            del suggestion_props["related_data_points"]


        queries = []
        params = {"suggestion_props": suggestion_props, "suggestion_id": data.suggestion.id}

        # Create Suggestion node
        suggestion_query = f"""
        MERGE (s:{self._suggestion_label} {{id: $suggestion_id}})
        SET s = $suggestion_props
        RETURN s
        """
        queries.append((suggestion_query, params.copy())) # Use params.copy() if params dict is modified later for action plan

        if data.action_plan:
            action_plan_props = data.action_plan.model_dump()
            action_plan_props["created_by_user_id"] = created_by_user_id # Assuming same creator for now
            action_plan_props["updated_by_user_id"] = created_by_user_id
            action_plan_props["created_at"] = data.action_plan.created_at.isoformat()
            action_plan_props["updated_at"] = data.action_plan.updated_at.isoformat()
            action_plan_props["steps_json"] = json.dumps([step.model_dump() for step in data.action_plan.steps])
            # Remove original list of step objects
            if "steps" in action_plan_props:
                del action_plan_props["steps"]

            params_ap = {"action_plan_props": action_plan_props, "action_plan_id": data.action_plan.id}

            # Create ActionPlan node
            action_plan_query = f"""
            MERGE (ap:{self._action_plan_label} {{id: $action_plan_id}})
            SET ap = $action_plan_props
            RETURN ap
            """
            queries.append((action_plan_query, params_ap))

            # Create relationship
            rel_params = {"suggestion_id": data.suggestion.id, "action_plan_id": data.action_plan.id}
            relationship_query = f"""
            MATCH (s:{self._suggestion_label} {{id: $suggestion_id}})
            MATCH (ap:{self._action_plan_label} {{id: $action_plan_id}})
            MERGE (s)-[r:{self._has_action_plan_rel}]->(ap)
            RETURN type(r)
            """
            queries.append((relationship_query, rel_params))

        try:
            # Execute queries in a single transaction ideally, or sequentially
            # For simplicity, let's assume execute_query can handle this or we run them one by one.
            # If Neo4jConnector doesn't support transactions directly via execute_query,
            # this part would need adjustment based on the driver's transaction handling.
            # For now, just executing them sequentially.

            await self.db.execute_query(suggestion_query, params)
            if data.action_plan:
                await self.db.execute_query(action_plan_query, params_ap)
                await self.db.execute_query(relationship_query, rel_params)

            return data # Return the input data, assuming IDs were pre-set by service or are part of model_dump

        except Exception as e:
            # Log the exception e
            raise DatabaseException(f"Error saving suggestion with plan: {e}", original_exception=e)

    # Other methods (get_suggestion_with_plan_by_id, update_action_plan, get_action_plan_by_id) will be added next.
    async def get_suggestion_with_plan_by_id(self, suggestion_id: str) -> Optional[SuggestionWithActionPlan]:
        query = f"""
        MATCH (s:{self._suggestion_label} {{id: $suggestion_id}})
        OPTIONAL MATCH (s)-[:{self._has_action_plan_rel}]->(ap:{self._action_plan_label})
        RETURN s, ap
        """
        params = {"suggestion_id": suggestion_id}
        try:
            results = await self.db.execute_query(query, params)
            if not results or not results[0] or not results[0].get("s"):
                return None

            record = results[0]
            suggestion_node_data = dict(record["s"]) # Convert Node to dict

            # Deserialize suggestion
            if "related_data_points_json" in suggestion_node_data and suggestion_node_data["related_data_points_json"]:
                suggestion_node_data["related_data_points"] = json.loads(suggestion_node_data["related_data_points_json"])
            del suggestion_node_data["related_data_points_json"] # remove to avoid Pydantic error

            suggestion = Suggestion(**suggestion_node_data)

            action_plan = None
            if record.get("ap"):
                action_plan_node_data = dict(record["ap"]) # Convert Node to dict
                if "steps_json" in action_plan_node_data and action_plan_node_data["steps_json"]:
                    steps_data = json.loads(action_plan_node_data["steps_json"])
                    action_plan_node_data["steps"] = [ActionPlanStep(**step_data) for step_data in steps_data]
                del action_plan_node_data["steps_json"]

                action_plan = ActionPlan(**action_plan_node_data)

            return SuggestionWithActionPlan(suggestion=suggestion, action_plan=action_plan)
        except json.JSONDecodeError as e:
            # Log this error
            raise DatabaseException(f"Error decoding JSON for suggestion {suggestion_id}: {e}", original_exception=e)
        except Exception as e:
            # Log other errors
            raise DatabaseException(f"Error retrieving suggestion {suggestion_id}: {e}", original_exception=e)

    async def get_action_plan_by_id(self, action_plan_id: str) -> Optional[ActionPlan]:
        query = f"""
        MATCH (ap:{self._action_plan_label} {{id: $action_plan_id}})
        RETURN ap
        """
        params = {"action_plan_id": action_plan_id}
        try:
            results = await self.db.execute_query(query, params)
            if not results or not results[0] or not results[0].get("ap"):
                return None

            action_plan_node_data = dict(results[0]["ap"])

            if "steps_json" in action_plan_node_data and action_plan_node_data["steps_json"]:
                steps_data = json.loads(action_plan_node_data["steps_json"])
                action_plan_node_data["steps"] = [ActionPlanStep(**step_data) for step_data in steps_data]
            if "steps_json" in action_plan_node_data: # Ensure key is removed even if None
                del action_plan_node_data["steps_json"]

            return ActionPlan(**action_plan_node_data)
        except json.JSONDecodeError as e:
            raise DatabaseException(f"Error decoding JSON for action plan {action_plan_id}: {e}", original_exception=e)
        except Exception as e:
            raise DatabaseException(f"Error retrieving action plan {action_plan_id}: {e}", original_exception=e)

    async def update_action_plan(self, action_plan: ActionPlan, updated_by_user_id: str) -> Optional[ActionPlan]:
        action_plan.updated_at = datetime.now(timezone.utc) # Ensure updated_at is fresh

        action_plan_props_to_update = {
            "suggestion_id": action_plan.suggestion_id,
            "title": action_plan.title,
            "overview": action_plan.overview,
            "steps_json": json.dumps([step.model_dump() for step in action_plan.steps]),
            "overall_status": action_plan.overall_status,
            "updated_at": action_plan.updated_at.isoformat(),
            "updated_by_user_id": updated_by_user_id
            # created_at and created_by_user_id should not change on update
            # id is used for matching, not setting
        }
        # Ensure all fields expected by the node are present, or use targeted SET operations

        query = f"""
        MATCH (ap:{self._action_plan_label} {{id: $action_plan_id}})
        SET ap.suggestion_id = $suggestion_id,
            ap.title = $title,
            ap.overview = $overview,
            ap.steps_json = $steps_json,
            ap.overall_status = $overall_status,
            ap.updated_at = $updated_at,
            ap.updated_by_user_id = $updated_by_user_id
            // Do not update ap.id, ap.created_at, ap.created_by_user_id
        RETURN ap
        """

        params = {
            "action_plan_id": action_plan.id,
            "suggestion_id": action_plan_props_to_update["suggestion_id"],
            "title": action_plan_props_to_update["title"],
            "overview": action_plan_props_to_update["overview"],
            "steps_json": action_plan_props_to_update["steps_json"],
            "overall_status": action_plan_props_to_update["overall_status"],
            "updated_at": action_plan_props_to_update["updated_at"],
            "updated_by_user_id": action_plan_props_to_update["updated_by_user_id"],
        }

        try:
            results = await self.db.execute_query(query, params)
            if not results or not results[0] or not results[0].get("ap"):
                raise NotFoundException(f"ActionPlan with id {action_plan.id} not found during update.")

            updated_node_data = dict(results[0]["ap"])
            if "steps_json" in updated_node_data and updated_node_data["steps_json"]:
                steps_data = json.loads(updated_node_data["steps_json"])
                updated_node_data["steps"] = [ActionPlanStep(**step_data) for step_data in steps_data]
            if "steps_json" in updated_node_data: # Ensure key is removed
                 del updated_node_data["steps_json"]

            return ActionPlan(**updated_node_data)
        except Exception as e:
            raise DatabaseException(f"Error updating action plan {action_plan.id}: {e}", original_exception=e)
