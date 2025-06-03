from typing import Optional, List
from uuid import UUID

from typing import Optional, List, Dict, Any # Added Dict, Any
from uuid import UUID

from src.data_models.client_preferences_models import (
    ClientPreference,
    ClientPreferenceCreate,
    ClientPreferenceUpdate,
)
from src.repositories.client_preference_repository import ClientPreferenceRepository
from src.neo4j_utils.connector import Neo4jConnector # Required for repository instantiation
from src.core.exceptions import NotFoundException, ServiceException # Changed to core.exceptions


class ClientPreferenceService:
    def __init__(self):
        # In a real app, Neo4jConnector might be injected or retrieved from a global/context var
        # For now, direct instantiation or a placeholder if connector setup is complex
        try:
            # This assumes Neo4jConnector can be instantiated without arguments or with defaults
            # from environment variables, as seen in other parts of the project.
            self.neo4j_connector = Neo4jConnector()
        except Exception as e:
            # Handle cases where Neo4jConnector might not be easily set up
            # This is a fallback to prevent crashes if DB connection is an issue.
            print(f"Warning: Neo4jConnector could not be initialized in ClientPreferenceService: {e}")
            self.neo4j_connector = None # Or a mock/dummy connector

        if self.neo4j_connector:
            self.repository = ClientPreferenceRepository(self.neo4j_connector)
        else:
            # If connector fails, service cannot operate with the DB.
            # This situation should be logged and handled appropriately.
            # For now, we'll let it proceed, but repository calls will fail.
            # In a robust app, this might raise a configuration error.
            self.repository = None
            print("Error: ClientPreferenceRepository could not be initialized due to missing Neo4jConnector.")


    async def create_preferences(self, data: ClientPreferenceCreate, created_by: str) -> ClientPreference:
        if not self.repository:
            raise ServiceException("ClientPreferenceService is not properly configured (repository missing).")

        # Check if preferences for this client_id already exist
        existing_preference = await self.repository.get_by_client_id(data.client_id)
        if existing_preference:
            raise ServiceException(f"Client preferences for client_id '{data.client_id}' already exist with id '{existing_preference.id}'.")

        try:
            return await self.repository.create(data, created_by)
        except Exception as e:
            # Log e
            raise ServiceException(f"Failed to create client preferences: {str(e)}")

    async def get_preferences_by_client_id(self, client_id: str) -> Optional[ClientPreference]:
        if not self.repository:
            raise ServiceException("ClientPreferenceService is not properly configured (repository missing).")
        try:
            preference = await self.repository.get_by_client_id(client_id)
            if not preference:
                return None # Or raise NotFoundException(f"No preferences found for client_id: {client_id}")
            return preference
        except Exception as e:
            raise ServiceException(f"Failed to retrieve preferences for client_id {client_id}: {str(e)}")

    async def get_preferences_by_id(self, preference_id: str) -> Optional[ClientPreference]:
        if not self.repository:
            raise ServiceException("ClientPreferenceService is not properly configured (repository missing).")
        try:
            # Basic validation for preference_id format, e.g. UUID
            try:
                UUID(preference_id, version=4)
            except ValueError:
                raise ServiceException(f"Invalid preference_id format: '{preference_id}'. Must be a valid UUID.")

            preference = await self.repository.get_by_id(preference_id)
            if not preference:
                return None # Or raise NotFoundException(f"Preferences not found with id: {preference_id}")
            return preference
        except ServiceException: # Re-raise ServiceExceptions (like invalid ID format)
            raise
        except Exception as e:
            raise ServiceException(f"Failed to retrieve preferences with id {preference_id}: {str(e)}")

    async def update_preferences(
        self, preference_id: str, data: ClientPreferenceUpdate, updated_by: str
    ) -> Optional[ClientPreference]:
        if not self.repository:
            raise ServiceException("ClientPreferenceService is not properly configured (repository missing).")

        # Validate ID
        try:
            UUID(preference_id, version=4)
        except ValueError:
            raise ServiceException(f"Invalid preference_id format: '{preference_id}'. Must be a valid UUID.")

        # Ensure the preference set exists before attempting update
        existing_preference = await self.repository.get_by_id(preference_id)
        if not existing_preference:
            raise NotFoundException(f"Preferences not found with id: {preference_id} for update.")

        try:
            updated_preference = await self.repository.update(preference_id, data, updated_by)
            if not updated_preference:
                 # This case might occur if the item was deleted between the get and update,
                 # or if the update operation itself failed to find/return the item.
                raise NotFoundException(f"Failed to update or find preferences after update for id: {preference_id}")
            return updated_preference
        except Exception as e:
            raise ServiceException(f"Failed to update preferences for id {preference_id}: {str(e)}")

    async def delete_preferences(self, preference_id: str, deleted_by: str) -> bool:
        if not self.repository:
            raise ServiceException("ClientPreferenceService is not properly configured (repository missing).")

        # Validate ID
        try:
            UUID(preference_id, version=4)
        except ValueError:
            raise ServiceException(f"Invalid preference_id format: '{preference_id}'. Must be a valid UUID.")

        # Check if it exists before trying to delete
        existing_preference = await self.repository.get_by_id(preference_id)
        if not existing_preference:
            raise NotFoundException(f"Preferences not found with id: {preference_id} for deletion.")

        try:
            deleted = await self.repository.delete(preference_id, deleted_by)
            return deleted
        except Exception as e:
            raise ServiceException(f"Failed to delete preferences with id {preference_id}: {str(e)}")

    async def close_db_connection(self):
        """Closes the database connection if the connector supports it."""
        if self.neo4j_connector and hasattr(self.neo4j_connector, 'close'):
            await self.neo4j_connector.close()
            print("Neo4j connection closed by ClientPreferenceService.")
        elif self.neo4j_connector : # if no close method, maybe log or do nothing
             print("Neo4j connector in ClientPreferenceService does not have a close method or it's not async.")
        else:
            print("No active Neo4j connection in ClientPreferenceService to close.")
