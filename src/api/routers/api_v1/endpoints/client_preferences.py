from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.auth.dependencies import get_current_active_user, require_permission
from src.auth.permissions import Permission # Will add new permissions later
from src.data_models.client_preferences_models import (
    ClientPreference,
    ClientPreferenceCreate,
    ClientPreferenceUpdate,
)
from src.services.client_preference_service import ClientPreferenceService
from src.core.exceptions import (
    NotFoundException as CoreNotFoundException,
    ServiceException as CoreServiceException,
    # DatabaseException is caught by CoreServiceException or generic Exception by decorator
)
from src.api.exceptions import (
    APINotFoundError,
    APIValidationError,
    # Import others if needed, or rely on decorator for 500
    handle_api_exceptions, # Renamed decorator
)


router = APIRouter()

# Placeholder for new permissions - will define these in permissions.py
# For now, using existing generic permissions as placeholders if specific ones aren't there.
# It's better to define them first, but for flow, let's assume they will be:
# Permission.CLIENT_PREFERENCES_CREATE, Permission.CLIENT_PREFERENCES_READ, etc.

def get_client_preference_service() -> ClientPreferenceService:
    return ClientPreferenceService()

@router.post(
    "/",
    response_model=ClientPreference,
    summary="Create new client preferences", # Added summary
    description="Create a new set of preferences for a client. Ensures client does not already have preferences.", # Added description
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.CLIENT_PREFERENCES_CREATE))]
)
@handle_api_exceptions("Create Client Preferences")
async def create_client_preferences(
    preference_data: ClientPreferenceCreate,
    service: ClientPreferenceService = Depends(get_client_preference_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user), # Assuming user ID is in "id"
):
    user_id = current_user.get("id", "unknown_user")
    return await service.create_preferences(preference_data, created_by=str(user_id))

@router.get(
    "/{client_id}",
    response_model=ClientPreference,
    summary="Get preferences by Client ID",
    description="Retrieve a specific client's preferences using their Client ID.",
    dependencies=[Depends(require_permission(Permission.CLIENT_PREFERENCES_READ))]
)
@handle_api_exceptions("Get Preferences by Client ID")
async def get_preferences_by_client_id(
    client_id: str,
    service: ClientPreferenceService = Depends(get_client_preference_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    preference = await service.get_preferences_by_client_id(client_id)
    if not preference:
        raise APINotFoundError(f"Preferences not found for client_id: {client_id}")
    return preference


@router.get(
    "/id/{preference_id}",
    response_model=ClientPreference,
    summary="Get preferences by Preference ID",
    description="Retrieve a specific set of preferences using its unique Preference ID.",
    dependencies=[Depends(require_permission(Permission.CLIENT_PREFERENCES_READ))]
)
@handle_api_exceptions("Get Preferences by ID")
async def get_preferences_by_id(
    preference_id: str,
    service: ClientPreferenceService = Depends(get_client_preference_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    preference = await service.get_preferences_by_id(preference_id)
    if not preference:
        raise APINotFoundError(f"Preferences not found with id: {preference_id}")
    return preference


@router.put(
    "/{preference_id}",
    response_model=ClientPreference,
    summary="Update client preferences",
    description="Update an existing set of client preferences by its Preference ID.",
    dependencies=[Depends(require_permission(Permission.CLIENT_PREFERENCES_UPDATE))]
)
@handle_api_exceptions("Update Client Preferences")
async def update_client_preferences(
    preference_id: str,
    preference_data: ClientPreferenceUpdate,
    service: ClientPreferenceService = Depends(get_client_preference_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = current_user.get("id", "unknown_user")
    updated_preference = await service.update_preferences(preference_id, preference_data, updated_by=str(user_id))
    return updated_preference


@router.delete(
    "/{preference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete client preferences",
    description="Delete a set of client preferences by its Preference ID.",
    dependencies=[Depends(require_permission(Permission.CLIENT_PREFERENCES_DELETE))]
)
@handle_api_exceptions("Delete Client Preferences")
async def delete_client_preferences(
    preference_id: str,
    service: ClientPreferenceService = Depends(get_client_preference_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = current_user.get("id", "unknown_user")
    await service.delete_preferences(preference_id, deleted_by=str(user_id))
    # No content returned, success is implied by 204 or handled by decorator for errors.

# Consider adding a startup/shutdown event for the router or app to manage service DB connections
# @router.on_event("shutdown")
# async def shutdown_event():
#     service = get_client_preference_service()
#     await service.close_db_connection()
