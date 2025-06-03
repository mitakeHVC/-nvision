from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from src.data_models.client_preferences_models import ClientPreference, ClientPreferenceCreate, ClientPreferenceUpdate
from src.neo4j_utils.connector import Neo4jConnector # Assuming Neo4j is used based on project structure
from src.core.exceptions import DatabaseException # Changed to core.exceptions

# This is a conceptual repository. Actual Neo4j queries would be more complex.
# For simplicity, it mimics document-like storage using node properties.

class ClientPreferenceRepository:
    _label = "ClientPreference"

    def __init__(self, neo4j_connector: Neo4jConnector):
        self.db = neo4j_connector
        self._ensure_constraints()

    def _ensure_constraints(self):
        """
        Ensure unique constraints for ClientPreference nodes.
        """
        try:
            self.db.execute_query(f"CREATE CONSTRAINT IF NOT EXISTS FOR (cp:{self._label}) REQUIRE cp.id IS UNIQUE")
            self.db.execute_query(f"CREATE CONSTRAINT IF NOT EXISTS FOR (cp:{self._label}) REQUIRE cp.client_id IS UNIQUE")
        except Exception as e:
            # Log this error, but don't necessarily block startup
            print(f"Warning: Could not ensure constraints for {self._label}: {e}")


    async def create(self, data: ClientPreferenceCreate, created_by: str) -> ClientPreference:
        preference_id = str(uuid.uuid4())
        now = datetime.utcnow()

        preference_data = {
            "id": preference_id,
            "client_id": data.client_id,
            "preferences_payload": data.preferences_payload, # Stored as a JSON string or directly if Neo4j handles dicts well
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": created_by,
            "last_updated_by": created_by,
            "version": 1,
            "is_deleted": False
        }

        query = f"""
        CREATE (cp:{self._label} $props)
        RETURN cp
        """
        try:
            result = await self.db.execute_query(query, {"props": preference_data})
            if result and result[0] and result[0]["cp"]:
                node = result[0]["cp"]
                return ClientPreference(
                    id=node["id"],
                    client_id=node["client_id"],
                    preferences_payload=node["preferences_payload"], # Neo4j might return it directly as dict
                    created_at=datetime.fromisoformat(node["created_at"]),
                    updated_at=datetime.fromisoformat(node["updated_at"])
                )
            else:
                raise DatabaseException("Failed to create client preference: No result returned.")
        except Exception as e:
            # Log the exception e
            raise DatabaseException(f"Error creating client preference: {e}")


    async def get_by_client_id(self, client_id: str) -> Optional[ClientPreference]:
        query = f"MATCH (cp:{self._label} {{client_id: $client_id, is_deleted: false}}) RETURN cp LIMIT 1"
        try:
            result = await self.db.execute_query(query, {"client_id": client_id})
            if result and result[0] and result[0]["cp"]:
                node = result[0]["cp"]
                return ClientPreference(
                    id=node["id"],
                    client_id=node["client_id"],
                    preferences_payload=node["preferences_payload"],
                    created_at=datetime.fromisoformat(node["created_at"]),
                    updated_at=datetime.fromisoformat(node["updated_at"])
                )
            return None
        except Exception as e:
            raise DatabaseException(f"Error fetching client preference by client_id: {e}")

    async def get_by_id(self, preference_id: str) -> Optional[ClientPreference]:
        query = f"MATCH (cp:{self._label} {{id: $preference_id, is_deleted: false}}) RETURN cp LIMIT 1"
        try:
            result = await self.db.execute_query(query, {"preference_id": preference_id})
            if result and result[0] and result[0]["cp"]:
                node = result[0]["cp"]
                return ClientPreference(
                    id=node["id"],
                    client_id=node["client_id"],
                    preferences_payload=node["preferences_payload"],
                    created_at=datetime.fromisoformat(node["created_at"]),
                    updated_at=datetime.fromisoformat(node["updated_at"])
                )
            return None
        except Exception as e:
            raise DatabaseException(f"Error fetching client preference by id: {e}")

    async def update(self, preference_id: str, data: ClientPreferenceUpdate, updated_by: str) -> Optional[ClientPreference]:
        now = datetime.utcnow()

        # Construct parts of the SET clause dynamically
        set_parts = ["cp.updated_at = $updated_at", "cp.last_updated_by = $updated_by", "cp.version = cp.version + 1"]
        params = {"preference_id": preference_id, "updated_at": now.isoformat(), "updated_by": updated_by}

        if data.preferences_payload is not None:
            # For Neo4j, if preferences_payload is a JSON string, you might need to handle it as such.
            # If it's stored as properties, you might merge maps or replace.
            # Assuming direct dictionary storage or JSON string for simplicity here.
            set_parts.append("cp.preferences_payload = $preferences_payload")
            params["preferences_payload"] = data.preferences_payload

        if not set_parts: # Should not happen if we always update timestamp and version
            return await self.get_by_id(preference_id)

        query = f"""
        MATCH (cp:{self._label} {{id: $preference_id, is_deleted: false}})
        SET {', '.join(set_parts)}
        RETURN cp
        """
        try:
            result = await self.db.execute_query(query, params)
            if result and result[0] and result[0]["cp"]:
                node = result[0]["cp"]
                return ClientPreference(
                    id=node["id"],
                    client_id=node["client_id"],
                    preferences_payload=node["preferences_payload"],
                    created_at=datetime.fromisoformat(node["created_at"]),
                    updated_at=datetime.fromisoformat(node["updated_at"])
                )
            return None # Or raise not found
        except Exception as e:
            raise DatabaseException(f"Error updating client preference: {e}")

    async def delete(self, preference_id: str, deleted_by: str) -> bool:
        # Soft delete by marking as deleted
        now = datetime.utcnow()
        query = f"""
        MATCH (cp:{self._label} {{id: $preference_id, is_deleted: false}})
        SET cp.is_deleted = true, cp.deleted_at = $deleted_at, cp.last_updated_by = $deleted_by
        RETURN count(cp) as count
        """
        params = {"preference_id": preference_id, "deleted_at": now.isoformat(), "deleted_by": deleted_by}
        try:
            result = await self.db.execute_query(query, params)
            return result and result[0] and result[0]["count"] > 0
        except Exception as e:
            raise DatabaseException(f"Error deleting client preference: {e}")

    # Potentially add a hard delete method if required
    # async def hard_delete(self, preference_id: str) -> bool:
    #     query = f"MATCH (cp:{self._label} {{id: $preference_id}}) DETACH DELETE cp RETURN count(cp) as count"
    #     # ...
