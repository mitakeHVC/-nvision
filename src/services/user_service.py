"""
ユーザーサービス

ユーザー管理のビジネスロジック、認証・認可処理、プロフィール管理を提供します。
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import logging

from ..models.user_models import (
    User, UserCreate, UserUpdate, UserInDB, UserProfile,
    UserPreferences, UserActivity, UserStats, UserSearchRequest,
    UserRoleAssignmentRequest, UserPermissionGrantRequest,
    BulkUserActionRequest, UserDashboardData, AdminUserOverview
)
from ..auth.models import LoginRequest, LoginResponse, PasswordChangeRequest
from ..auth.auth_service import AuthService, LoginResult
from ..auth.permissions import PermissionManager, Permission, Role
from ..repositories.user_repository import UserRepository
from .base import BaseService

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """ユーザーサービス"""
    
    def __init__(
        self,
        user_repository: UserRepository,
        auth_service: AuthService,
        permission_manager: PermissionManager
    ):
        """
        ユーザーサービスを初期化
        
        Args:
            user_repository: ユーザーリポジトリ
            auth_service: 認証サービス
            permission_manager: 権限マネージャー
        """
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.permission_manager = permission_manager
    
    async def register_user(
        self,
        user_data: UserCreate,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ユーザーを登録
        
        Args:
            user_data: ユーザー作成データ
            created_by: 作成者のユーザーID
            
        Returns:
            登録結果
        """
        try:
            # 認証サービスを使用してユーザー登録
            result = self.auth_service.register_user(
                username=user_data.username,
                email=user_data.email,
                password=user_data.password,
                user_repository=self.user_repository,
                roles=user_data.roles
            )
            
            if not result["success"]:
                return result
            
            # 追加のプロフィール情報を設定
            user_id = result["user_id"]
            if user_data.first_name or user_data.last_name:
                update_data = UserUpdate(
                    first_name=user_data.first_name,
                    last_name=user_data.last_name
                )
                await self.user_repository.update_user(user_id, update_data)
            
            # ユーザー情報を取得
            user = await self.get_user_by_id(user_id)
            
            logger.info(f"User registered: {user_id} by {created_by or 'self'}")
            
            return {
                "success": True,
                "message": "User registered successfully",
                "user": user,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            return {
                "success": False,
                "error": "Registration failed due to internal error"
            }
    
    async def authenticate_user(self, login_request: LoginRequest) -> LoginResult:
        """
        ユーザー認証
        
        Args:
            login_request: ログインリクエスト
            
        Returns:
            認証結果
        """
        try:
            return self.auth_service.authenticate_user(
                username_or_email=login_request.username_or_email,
                password=login_request.password,
                user_repository=self.user_repository
            )
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return LoginResult(
                success=False,
                error_message="Authentication failed due to internal error"
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        IDでユーザーを取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ユーザー、または None
        """
        try:
            user_in_db = await self.user_repository.get_user_by_id(user_id)
            if not user_in_db:
                return None
            
            return self._convert_to_user(user_in_db)
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        ユーザー名でユーザーを取得
        
        Args:
            username: ユーザー名
            
        Returns:
            ユーザー、または None
        """
        try:
            user_in_db = await self.user_repository.get_user_by_username(username)
            if not user_in_db:
                return None
            
            return self._convert_to_user(user_in_db)
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        メールアドレスでユーザーを取得
        
        Args:
            email: メールアドレス
            
        Returns:
            ユーザー、または None
        """
        try:
            user_in_db = await self.user_repository.get_user_by_email(email)
            if not user_in_db:
                return None
            
            return self._convert_to_user(user_in_db)
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    async def update_user(
        self,
        user_id: str,
        user_data: UserUpdate,
        updated_by: str
    ) -> Optional[User]:
        """
        ユーザーを更新
        
        Args:
            user_id: ユーザーID
            user_data: 更新データ
            updated_by: 更新者のユーザーID
            
        Returns:
            更新されたユーザー、または None
        """
        try:
            # 権限チェック
            if not await self._can_modify_user(updated_by, user_id):
                logger.warning(f"User {updated_by} attempted to modify user {user_id} without permission")
                return None
            
            # ユーザー更新
            updated_user = await self.user_repository.update_user(user_id, user_data)
            if not updated_user:
                return None
            
            # ロール更新
            if user_data.roles is not None:
                await self._update_user_roles(user_id, user_data.roles, updated_by)
            
            logger.info(f"User {user_id} updated by {updated_by}")
            return self._convert_to_user(updated_user)
            
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None
    
    async def delete_user(self, user_id: str, deleted_by: str) -> bool:
        """
        ユーザーを削除
        
        Args:
            user_id: ユーザーID
            deleted_by: 削除者のユーザーID
            
        Returns:
            成功した場合 True
        """
        try:
            # 権限チェック
            if not await self._can_delete_user(deleted_by, user_id):
                logger.warning(f"User {deleted_by} attempted to delete user {user_id} without permission")
                return False
            
            # 自分自身の削除を防ぐ
            if user_id == deleted_by:
                logger.warning(f"User {user_id} attempted to delete themselves")
                return False
            
            # ユーザー削除
            success = await self.user_repository.delete_user(user_id)
            if success:
                # 権限マネージャーからも削除
                self.permission_manager.clear_user_permissions(user_id)
                logger.info(f"User {user_id} deleted by {deleted_by}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    async def search_users(
        self,
        search_request: UserSearchRequest,
        requester_id: str
    ) -> Tuple[List[User], int]:
        """
        ユーザーを検索
        
        Args:
            search_request: 検索リクエスト
            requester_id: リクエスト者のユーザーID
            
        Returns:
            (ユーザーリスト, 総件数)
        """
        try:
            # 権限チェック
            if not self.permission_manager.has_permission(requester_id, Permission.USER_LIST):
                logger.warning(f"User {requester_id} attempted to search users without permission")
                return [], 0
            
            users_in_db, total = await self.user_repository.search_users(search_request)
            users = [self._convert_to_user(user) for user in users_in_db]
            
            return users, total
            
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            return [], 0
    
    async def assign_roles_to_user(
        self,
        request: UserRoleAssignmentRequest,
        assigned_by: str
    ) -> bool:
        """
        ユーザーにロールを割り当て
        
        Args:
            request: ロール割り当てリクエスト
            assigned_by: 割り当て者のユーザーID
            
        Returns:
            成功した場合 True
        """
        try:
            # 権限チェック
            if not self.permission_manager.has_permission(assigned_by, Permission.USER_UPDATE):
                logger.warning(f"User {assigned_by} attempted to assign roles without permission")
                return False
            
            # ユーザー存在チェック
            user = await self.user_repository.get_user_by_id(request.user_id)
            if not user:
                return False
            
            # 現在のロールをクリア
            current_roles = self.permission_manager.get_user_roles(request.user_id)
            for role in current_roles:
                self.permission_manager.remove_role_from_user(request.user_id, role)
            
            # 新しいロールを割り当て
            for role_name in request.role_names:
                self.permission_manager.assign_role_to_user(request.user_id, role_name)
            
            # ユーザーのロール情報を更新
            user_update = UserUpdate(roles=request.role_names)
            await self.user_repository.update_user(request.user_id, user_update)
            
            logger.info(f"Roles {request.role_names} assigned to user {request.user_id} by {assigned_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign roles to user {request.user_id}: {e}")
            return False
    
    async def grant_permissions_to_user(
        self,
        request: UserPermissionGrantRequest,
        granted_by: str
    ) -> bool:
        """
        ユーザーに権限を付与
        
        Args:
            request: 権限付与リクエスト
            granted_by: 付与者のユーザーID
            
        Returns:
            成功した場合 True
        """
        try:
            # 権限チェック
            if not self.permission_manager.has_permission(granted_by, Permission.USER_UPDATE):
                logger.warning(f"User {granted_by} attempted to grant permissions without permission")
                return False
            
            # ユーザー存在チェック
            user = await self.user_repository.get_user_by_id(request.user_id)
            if not user:
                return False
            
            # 権限を付与
            for permission_name in request.permission_names:
                try:
                    permission = Permission(permission_name)
                    self.permission_manager.grant_permission_to_user(request.user_id, permission)
                except ValueError:
                    logger.warning(f"Invalid permission: {permission_name}")
                    continue
            
            logger.info(f"Permissions {request.permission_names} granted to user {request.user_id} by {granted_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant permissions to user {request.user_id}: {e}")
            return False
    
    async def change_password(
        self,
        user_id: str,
        password_request: PasswordChangeRequest
    ) -> Dict[str, Any]:
        """
        パスワードを変更
        
        Args:
            user_id: ユーザーID
            password_request: パスワード変更リクエスト
            
        Returns:
            変更結果
        """
        try:
            return self.auth_service.change_password(
                user_id=user_id,
                current_password=password_request.current_password,
                new_password=password_request.new_password,
                user_repository=self.user_repository
            )
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            return {"success": False, "error": "Password change failed"}
    
    async def get_user_dashboard_data(self, user_id: str) -> Optional[UserDashboardData]:
        """
        ユーザーダッシュボードデータを取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ダッシュボードデータ、または None
        """
        try:
            # 基本的なダミーデータを返す（実際の実装では各リポジトリから取得）
            user = await self.get_user_by_id(user_id)
            if not user:
                return None
            
            # プロフィール情報
            profile = UserProfile(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                first_name=getattr(user, 'first_name', None),
                last_name=getattr(user, 'last_name', None),
                created_at=user.created_at,
                updated_at=datetime.now(timezone.utc),
                last_login=user.last_login,
                is_active=getattr(user, 'is_active', True),
                email_verified=getattr(user, 'email_verified', False)
            )
            
            # 統計情報
            stats = UserStats(
                user_id=user_id,
                created_at=user.created_at,
                updated_at=datetime.now(timezone.utc)
            )
            
            # 設定情報
            preferences = UserPreferences(
                user_id=user_id,
                created_at=user.created_at,
                updated_at=datetime.now(timezone.utc)
            )
            
            return UserDashboardData(
                user=profile,
                stats=stats,
                recent_activities=[],
                active_sessions=[],
                notifications=[],
                api_keys=[],
                preferences=preferences
            )
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data for user {user_id}: {e}")
            return None
    
    async def get_admin_overview(self, admin_user_id: str) -> Optional[AdminUserOverview]:
        """
        管理者用ユーザー概要を取得
        
        Args:
            admin_user_id: 管理者ユーザーID
            
        Returns:
            管理者用概要、または None
        """
        try:
            # 権限チェック
            if not self.permission_manager.has_permission(admin_user_id, Permission.USER_LIST):
                return None
            
            # 基本的なダミーデータを返す（実際の実装では統計を計算）
            return AdminUserOverview(
                total_users=len(self.user_repository._users),
                active_users=len([u for u in self.user_repository._users.values() if u.is_active]),
                inactive_users=len([u for u in self.user_repository._users.values() if not u.is_active]),
                new_users_today=0,
                new_users_this_week=0,
                new_users_this_month=0,
                users_by_role={},
                recent_registrations=[],
                recent_logins=[],
                security_alerts=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to get admin overview: {e}")
            return None
    
    async def bulk_user_action(
        self,
        request: BulkUserActionRequest,
        performed_by: str
    ) -> Dict[str, Any]:
        """
        一括ユーザー操作
        
        Args:
            request: 一括操作リクエスト
            performed_by: 実行者のユーザーID
            
        Returns:
            操作結果
        """
        try:
            # 権限チェック
            if not self.permission_manager.has_permission(performed_by, Permission.USER_UPDATE):
                return {"success": False, "error": "Insufficient permissions"}
            
            success_count = 0
            failed_count = 0
            errors = []
            
            for user_id in request.user_ids:
                try:
                    if request.action == "activate":
                        update_data = UserUpdate(is_active=True)
                        result = await self.user_repository.update_user(user_id, update_data)
                        if result:
                            success_count += 1
                        else:
                            failed_count += 1
                    
                    elif request.action == "deactivate":
                        update_data = UserUpdate(is_active=False)
                        result = await self.user_repository.update_user(user_id, update_data)
                        if result:
                            success_count += 1
                        else:
                            failed_count += 1
                    
                    elif request.action == "delete":
                        result = await self.delete_user(user_id, performed_by)
                        if result:
                            success_count += 1
                        else:
                            failed_count += 1
                    
                    else:
                        errors.append(f"Unknown action: {request.action}")
                        failed_count += 1
                
                except Exception as e:
                    errors.append(f"Failed to process user {user_id}: {str(e)}")
                    failed_count += 1
            
            logger.info(f"Bulk action {request.action} performed by {performed_by}: {success_count} success, {failed_count} failed")
            
            return {
                "success": True,
                "message": f"Bulk action completed: {success_count} success, {failed_count} failed",
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Bulk user action failed: {e}")
            return {"success": False, "error": "Bulk action failed"}
    
    async def check_username_availability(self, username: str) -> bool:
        """ユーザー名の利用可能性をチェック"""
        try:
            return not await self.user_repository.username_exists(username)
        except Exception as e:
            logger.error(f"Failed to check username availability: {e}")
            return False
    
    async def check_email_availability(self, email: str) -> bool:
        """メールアドレスの利用可能性をチェック"""
        try:
            return not await self.user_repository.email_exists(email)
        except Exception as e:
            logger.error(f"Failed to check email availability: {e}")
            return False
    
    # === プライベートメソッド ===
    
    def _convert_to_user(self, user_in_db: UserInDB) -> User:
        """UserInDBをUserに変換"""
        return User(
            user_id=user_in_db.user_id,
            username=user_in_db.username,
            email=user_in_db.email,
            first_name=user_in_db.first_name,
            last_name=user_in_db.last_name,
            is_active=user_in_db.is_active,
            status=user_in_db.status,
            roles=user_in_db.roles,
            permissions=user_in_db.permissions,
            created_at=user_in_db.created_at,
            last_login=user_in_db.last_login,
            email_verified=user_in_db.email_verified
        )
    
    async def _can_modify_user(self, modifier_id: str, target_user_id: str) -> bool:
        """ユーザー変更権限をチェック"""
        # 自分自身は変更可能
        if modifier_id == target_user_id:
            return True
        
        # USER_UPDATE権限があれば変更可能
        return self.permission_manager.has_permission(modifier_id, Permission.USER_UPDATE)
    
    async def _can_delete_user(self, deleter_id: str, target_user_id: str) -> bool:
        """ユーザー削除権限をチェック"""
        # 自分自身は削除不可
        if deleter_id == target_user_id:
            return False
        
        # USER_DELETE権限が必要
        return self.permission_manager.has_permission(deleter_id, Permission.USER_DELETE)
    
    async def _update_user_roles(self, user_id: str, roles: List[str], updated_by: str):
        """ユーザーロールを更新"""
        try:
            # 現在のロールをクリア
            current_roles = self.permission_manager.get_user_roles(user_id)
            for role in current_roles:
                self.permission_manager.remove_role_from_user(user_id, role)
            
            # 新しいロールを割り当て
            for role in roles:
                self.permission_manager.assign_role_to_user(user_id, role)
            
            logger.info(f"User {user_id} roles updated to {roles} by {updated_by}")
            
        except Exception as e:
            logger.error(f"Failed to update user roles: {e}")