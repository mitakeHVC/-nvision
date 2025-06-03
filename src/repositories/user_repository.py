"""
ユーザーリポジトリ

ユーザーデータの永続化、ロール・権限管理、セッション管理を提供します。
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import logging
import uuid
from abc import ABC, abstractmethod

from ..models.user_models import (
    User, UserCreate, UserUpdate, UserInDB, UserProfile,
    UserPreferences, UserActivity, UserStats, UserRole,
    UserPermission, UserGroup, UserDevice, UserNotification,
    UserApiKey, UserAuditLog, UserSearchRequest
)
from ..auth.models import LoginAttempt, SecurityEvent
from .base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepositoryInterface(ABC):
    """ユーザーリポジトリインターフェース"""
    
    @abstractmethod
    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """ユーザーを作成"""
        pass
    
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """IDでユーザーを取得"""
        pass
    
    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """ユーザー名でユーザーを取得"""
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """メールアドレスでユーザーを取得"""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[UserInDB]:
        """ユーザーを更新"""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """ユーザーを削除"""
        pass


class UserRepository(BaseRepository, UserRepositoryInterface):
    """ユーザーリポジトリ実装"""
    
    def __init__(self, connection_manager):
        """
        ユーザーリポジトリを初期化
        
        Args:
            connection_manager: データベース接続マネージャー
        """
        super().__init__(connection_manager)
        
        # インメモリストレージ（実際の実装ではデータベースを使用）
        self._users: Dict[str, UserInDB] = {}
        self._users_by_username: Dict[str, str] = {}
        self._users_by_email: Dict[str, str] = {}
        self._user_profiles: Dict[str, UserProfile] = {}
        self._user_preferences: Dict[str, UserPreferences] = {}
        self._user_activities: Dict[str, List[UserActivity]] = {}
        self._user_stats: Dict[str, UserStats] = {}
        self._user_roles: Dict[str, List[UserRole]] = {}
        self._user_permissions: Dict[str, List[UserPermission]] = {}
        self._user_groups: Dict[str, UserGroup] = {}
        self._user_devices: Dict[str, List[UserDevice]] = {}
        self._user_notifications: Dict[str, List[UserNotification]] = {}
        self._user_api_keys: Dict[str, List[UserApiKey]] = {}
        self._user_audit_logs: Dict[str, List[UserAuditLog]] = {}
        self._login_attempts: List[LoginAttempt] = []
        self._security_events: List[SecurityEvent] = []
    
    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """
        ユーザーを作成
        
        Args:
            user_data: ユーザー作成データ
            
        Returns:
            作成されたユーザー
            
        Raises:
            ValueError: ユーザー名またはメールが既に存在する場合
        """
        try:
            # 重複チェック
            if await self.username_exists(user_data.username):
                raise ValueError(f"Username '{user_data.username}' already exists")
            
            if await self.email_exists(user_data.email):
                raise ValueError(f"Email '{user_data.email}' already exists")
            
            # ユーザーID生成
            user_id = str(uuid.uuid4())
            current_time = datetime.now(timezone.utc)
            
            # ユーザーオブジェクト作成
            user = UserInDB(
                user_id=user_id,
                username=user_data.username,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                password_hash="",  # 実際の実装では暗号化されたパスワード
                is_active=user_data.is_active,
                roles=user_data.roles or ["viewer"],
                permissions=[],
                created_at=current_time,
                updated_at=current_time
            )
            
            # ストレージに保存
            self._users[user_id] = user
            self._users_by_username[user_data.username.lower()] = user_id
            self._users_by_email[user_data.email.lower()] = user_id
            
            # 初期プロフィール作成
            await self._create_initial_profile(user)
            
            # 初期設定作成
            await self._create_initial_preferences(user)
            
            # 初期統計作成
            await self._create_initial_stats(user)
            
            # 監査ログ記録
            await self._log_user_action(
                user_id, "user_created", "user", user_id,
                new_values={"username": user.username, "email": user.email}
            )
            
            logger.info(f"User created: {user_id} ({user.username})")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        IDでユーザーを取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ユーザー、または None
        """
        try:
            return self._users.get(user_id)
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """
        ユーザー名でユーザーを取得
        
        Args:
            username: ユーザー名
            
        Returns:
            ユーザー、または None
        """
        try:
            user_id = self._users_by_username.get(username.lower())
            if user_id:
                return self._users.get(user_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """
        メールアドレスでユーザーを取得
        
        Args:
            email: メールアドレス
            
        Returns:
            ユーザー、または None
        """
        try:
            user_id = self._users_by_email.get(email.lower())
            if user_id:
                return self._users.get(user_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    async def get_user_by_username_or_email(self, username_or_email: str) -> Optional[UserInDB]:
        """
        ユーザー名またはメールアドレスでユーザーを取得
        
        Args:
            username_or_email: ユーザー名またはメールアドレス
            
        Returns:
            ユーザー、または None
        """
        # メールアドレス形式かチェック
        if "@" in username_or_email:
            return await self.get_user_by_email(username_or_email)
        else:
            return await self.get_user_by_username(username_or_email)
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[UserInDB]:
        """
        ユーザーを更新
        
        Args:
            user_id: ユーザーID
            user_data: 更新データ
            
        Returns:
            更新されたユーザー、または None
        """
        try:
            user = self._users.get(user_id)
            if not user:
                return None
            
            # 変更前の値を記録
            old_values = {}
            new_values = {}
            
            # 更新処理
            update_data = user_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(user, field):
                    old_values[field] = getattr(user, field)
                    setattr(user, field, value)
                    new_values[field] = value
            
            user.updated_at = datetime.now(timezone.utc)
            
            # メールアドレスが変更された場合、インデックスを更新
            if "email" in update_data:
                # 古いメールアドレスのインデックスを削除
                old_email = old_values.get("email")
                if old_email and old_email.lower() in self._users_by_email:
                    del self._users_by_email[old_email.lower()]
                
                # 新しいメールアドレスのインデックスを追加
                self._users_by_email[user.email.lower()] = user_id
            
            # 監査ログ記録
            await self._log_user_action(
                user_id, "user_updated", "user", user_id,
                old_values=old_values, new_values=new_values
            )
            
            logger.info(f"User updated: {user_id}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None
    
    async def delete_user(self, user_id: str) -> bool:
        """
        ユーザーを削除
        
        Args:
            user_id: ユーザーID
            
        Returns:
            成功した場合 True
        """
        try:
            user = self._users.get(user_id)
            if not user:
                return False
            
            # インデックスから削除
            if user.username.lower() in self._users_by_username:
                del self._users_by_username[user.username.lower()]
            
            if user.email.lower() in self._users_by_email:
                del self._users_by_email[user.email.lower()]
            
            # 関連データを削除
            self._user_profiles.pop(user_id, None)
            self._user_preferences.pop(user_id, None)
            self._user_activities.pop(user_id, None)
            self._user_stats.pop(user_id, None)
            self._user_roles.pop(user_id, None)
            self._user_permissions.pop(user_id, None)
            self._user_devices.pop(user_id, None)
            self._user_notifications.pop(user_id, None)
            self._user_api_keys.pop(user_id, None)
            self._user_audit_logs.pop(user_id, None)
            
            # ユーザーを削除
            del self._users[user_id]
            
            # 監査ログ記録
            await self._log_user_action(
                user_id, "user_deleted", "user", user_id,
                old_values={"username": user.username, "email": user.email}
            )
            
            logger.info(f"User deleted: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    async def search_users(self, search_request: UserSearchRequest) -> Tuple[List[UserInDB], int]:
        """
        ユーザーを検索
        
        Args:
            search_request: 検索リクエスト
            
        Returns:
            (ユーザーリスト, 総件数)
        """
        try:
            users = list(self._users.values())
            
            # フィルタリング
            if search_request.query:
                query = search_request.query.lower()
                users = [
                    user for user in users
                    if (query in user.username.lower() or
                        query in user.email.lower() or
                        (user.first_name and query in user.first_name.lower()) or
                        (user.last_name and query in user.last_name.lower()))
                ]
            
            if search_request.roles:
                users = [
                    user for user in users
                    if any(role in user.roles for role in search_request.roles)
                ]
            
            if search_request.is_active is not None:
                users = [user for user in users if user.is_active == search_request.is_active]
            
            if search_request.created_after:
                users = [user for user in users if user.created_at >= search_request.created_after]
            
            if search_request.created_before:
                users = [user for user in users if user.created_at <= search_request.created_before]
            
            total = len(users)
            
            # ソート
            reverse = search_request.sort_order == "desc"
            users.sort(key=lambda x: getattr(x, search_request.sort_by, x.created_at), reverse=reverse)
            
            # ページネーション
            start = (search_request.page - 1) * search_request.per_page
            end = start + search_request.per_page
            users = users[start:end]
            
            return users, total
            
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            return [], 0
    
    async def username_exists(self, username: str) -> bool:
        """ユーザー名の存在チェック"""
        return username.lower() in self._users_by_username
    
    async def email_exists(self, email: str) -> bool:
        """メールアドレスの存在チェック"""
        return email.lower() in self._users_by_email
    
    async def update_last_login(self, user_id: str) -> bool:
        """最終ログイン時刻を更新"""
        try:
            user = self._users.get(user_id)
            if not user:
                return False
            
            user.last_login = datetime.now(timezone.utc)
            user.login_count += 1
            user.failed_login_attempts = 0  # リセット
            user.last_failed_login = None
            
            # 統計更新
            await self._update_user_stats(user_id, "login")
            
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            return False
    
    async def record_failed_login(self, user_id: str) -> bool:
        """ログイン失敗を記録"""
        try:
            user = self._users.get(user_id)
            if not user:
                return False
            
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.now(timezone.utc)
            
            return True
        except Exception as e:
            logger.error(f"Failed to record failed login for user {user_id}: {e}")
            return False
    
    async def update_password_hash(self, user_id: str, password_hash: str) -> bool:
        """パスワードハッシュを更新"""
        try:
            user = self._users.get(user_id)
            if not user:
                return False
            
            old_hash = user.password_hash
            user.password_hash = password_hash
            user.password_changed_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            
            # 監査ログ記録
            await self._log_user_action(
                user_id, "password_changed", "user", user_id,
                old_values={"password_hash": old_hash[:10] + "..."},
                new_values={"password_hash": password_hash[:10] + "..."}
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to update password for user {user_id}: {e}")
            return False
    
    # === プライベートメソッド ===
    
    async def _create_initial_profile(self, user: UserInDB):
        """初期プロフィールを作成"""
        profile = UserProfile(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_active=user.is_active,
            email_verified=user.email_verified
        )
        self._user_profiles[user.user_id] = profile
    
    async def _create_initial_preferences(self, user: UserInDB):
        """初期設定を作成"""
        preferences = UserPreferences(
            user_id=user.user_id,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        self._user_preferences[user.user_id] = preferences
    
    async def _create_initial_stats(self, user: UserInDB):
        """初期統計を作成"""
        stats = UserStats(
            user_id=user.user_id,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        self._user_stats[user.user_id] = stats
    
    async def _update_user_stats(self, user_id: str, action: str):
        """ユーザー統計を更新"""
        stats = self._user_stats.get(user_id)
        if not stats:
            return
        
        if action == "login":
            stats.total_logins += 1
            stats.last_login = datetime.now(timezone.utc)
        
        stats.updated_at = datetime.now(timezone.utc)
    
    async def _log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """ユーザーアクションをログ"""
        log_entry = UserAuditLog(
            log_id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        
        if user_id not in self._user_audit_logs:
            self._user_audit_logs[user_id] = []
        
        self._user_audit_logs[user_id].append(log_entry)
        
        # ログ履歴の制限（最新1000件のみ保持）
        if len(self._user_audit_logs[user_id]) > 1000:
            self._user_audit_logs[user_id] = self._user_audit_logs[user_id][-1000:]