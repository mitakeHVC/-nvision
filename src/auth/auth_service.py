"""
認証サービス

ユーザー認証、ログイン、ログアウト、トークン管理の機能を提供します。
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import logging
from dataclasses import dataclass

from .jwt_handler import JWTHandler, TokenData
from .password_handler import PasswordHandler
from .permissions import PermissionManager, Permission, Role

logger = logging.getLogger(__name__)


@dataclass
class LoginResult:
    """ログイン結果"""
    success: bool
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None


@dataclass
class AuthUser:
    """認証ユーザー情報"""
    user_id: str
    username: str
    email: str
    roles: list[str]
    permissions: list[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class AuthService:
    """認証サービス"""
    
    def __init__(
        self,
        jwt_handler: JWTHandler,
        password_handler: PasswordHandler,
        permission_manager: PermissionManager
    ):
        """
        認証サービスを初期化
        
        Args:
            jwt_handler: JWT ハンドラー
            password_handler: パスワードハンドラー
            permission_manager: 権限マネージャー
        """
        self.jwt_handler = jwt_handler
        self.password_handler = password_handler
        self.permission_manager = permission_manager
        
        # セッション管理（実際の実装ではRedisなどを使用）
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._failed_login_attempts: Dict[str, list] = {}
        
        # セキュリティ設定
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 15
        self.session_timeout_hours = 24
    
    def authenticate_user(
        self,
        username_or_email: str,
        password: str,
        user_repository  # 実際のユーザーリポジトリ
    ) -> LoginResult:
        """
        ユーザー認証
        
        Args:
            username_or_email: ユーザー名またはメールアドレス
            password: パスワード
            user_repository: ユーザーリポジトリ
            
        Returns:
            ログイン結果
        """
        try:
            # アカウントロックチェック
            if self._is_account_locked(username_or_email):
                return LoginResult(
                    success=False,
                    error_message="Account is temporarily locked due to multiple failed login attempts"
                )
            
            # ユーザー検索（実際の実装では user_repository を使用）
            user_data = self._get_user_by_username_or_email(username_or_email, user_repository)
            
            if not user_data:
                self._record_failed_attempt(username_or_email)
                return LoginResult(
                    success=False,
                    error_message="Invalid username or password"
                )
            
            # アクティブユーザーチェック
            if not user_data.get("is_active", True):
                return LoginResult(
                    success=False,
                    error_message="Account is deactivated"
                )
            
            # パスワード検証
            stored_password_hash = user_data.get("password_hash")
            if not self.password_handler.verify_password(password, stored_password_hash):
                self._record_failed_attempt(username_or_email)
                return LoginResult(
                    success=False,
                    error_message="Invalid username or password"
                )
            
            # 認証成功
            self._clear_failed_attempts(username_or_email)
            
            # ユーザー権限を取得
            user_id = user_data["user_id"]
            roles = self.permission_manager.get_user_roles(user_id)
            permissions = self.permission_manager.get_user_permissions(user_id)
            
            # トークン生成
            access_token = self.jwt_handler.create_access_token(
                user_id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                roles=roles,
                permissions=permissions
            )
            
            refresh_token = self.jwt_handler.create_refresh_token(user_id)
            
            # セッション作成
            session_id = self._create_session(user_id, access_token)
            
            # 最終ログイン時刻を更新（実際の実装では user_repository を使用）
            self._update_last_login(user_id, user_repository)
            
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.jwt_handler.access_token_expire_minutes
            )
            
            logger.info(f"User {user_id} authenticated successfully")
            
            return LoginResult(
                success=True,
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                user_data={
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "roles": roles,
                    "permissions": permissions,
                    "session_id": session_id
                }
            )
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return LoginResult(
                success=False,
                error_message="Authentication failed due to internal error"
            )
    
    def logout_user(self, access_token: str, user_id: Optional[str] = None) -> bool:
        """
        ユーザーログアウト
        
        Args:
            access_token: アクセストークン
            user_id: ユーザーID（オプション）
            
        Returns:
            成功した場合 True
        """
        try:
            # トークンをブラックリストに追加
            self.jwt_handler.blacklist_token(access_token)
            
            # セッション削除
            if user_id:
                self._remove_session(user_id)
            
            logger.info(f"User {user_id or 'unknown'} logged out")
            return True
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    def refresh_token(
        self,
        refresh_token: str,
        user_repository  # 実際のユーザーリポジトリ
    ) -> Optional[str]:
        """
        アクセストークンをリフレッシュ
        
        Args:
            refresh_token: リフレッシュトークン
            user_repository: ユーザーリポジトリ
            
        Returns:
            新しいアクセストークン、または None（失敗時）
        """
        try:
            # リフレッシュトークン検証
            payload = self.jwt_handler.verify_token(refresh_token)
            if not payload or payload.get("type") != "refresh":
                return None
            
            user_id = payload["sub"]
            
            # ユーザー情報を取得
            user_data = self._get_user_by_id(user_id, user_repository)
            if not user_data or not user_data.get("is_active", True):
                return None
            
            # 権限を取得
            roles = self.permission_manager.get_user_roles(user_id)
            permissions = self.permission_manager.get_user_permissions(user_id)
            
            # 新しいアクセストークンを生成
            new_access_token = self.jwt_handler.create_access_token(
                user_id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                roles=roles,
                permissions=permissions
            )
            
            logger.info(f"Access token refreshed for user {user_id}")
            return new_access_token
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def validate_token(self, access_token: str) -> Optional[AuthUser]:
        """
        アクセストークンを検証してユーザー情報を取得
        
        Args:
            access_token: アクセストークン
            
        Returns:
            認証ユーザー情報、または None（無効な場合）
        """
        try:
            token_data = self.jwt_handler.get_token_data(access_token)
            if not token_data:
                return None
            
            # セッション確認
            if not self._is_session_valid(token_data.user_id):
                return None
            
            return AuthUser(
                user_id=token_data.user_id,
                username=token_data.username,
                email=token_data.email,
                roles=token_data.roles,
                permissions=token_data.permissions,
                is_active=True,
                created_at=token_data.iat,
                last_login=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """
        ユーザーの権限をチェック
        
        Args:
            user_id: ユーザーID
            permission: チェックする権限
            
        Returns:
            権限を持っている場合 True
        """
        return self.permission_manager.has_permission(user_id, permission)
    
    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        user_repository,  # 実際のユーザーリポジトリ
        roles: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        新規ユーザー登録
        
        Args:
            username: ユーザー名
            email: メールアドレス
            password: パスワード
            roles: 初期ロール
            user_repository: ユーザーリポジトリ
            
        Returns:
            登録結果
        """
        try:
            # パスワード強度チェック
            if not self.password_handler.is_password_secure(password):
                strength_info = self.password_handler.check_password_strength(password)
                return {
                    "success": False,
                    "error": "Password is not secure enough",
                    "password_issues": strength_info["issues"],
                    "suggestions": strength_info["suggestions"]
                }
            
            # ユーザー名・メール重複チェック（実際の実装では user_repository を使用）
            if self._user_exists(username, email, user_repository):
                return {
                    "success": False,
                    "error": "Username or email already exists"
                }
            
            # パスワードハッシュ化
            password_hash = self.password_handler.hash_password(password)
            
            # ユーザー作成（実際の実装では user_repository を使用）
            user_id = self._create_user(
                username, email, password_hash, user_repository
            )
            
            # デフォルトロール設定
            if not roles:
                roles = [Role.VIEWER.value]
            
            for role in roles:
                self.permission_manager.assign_role_to_user(user_id, role)
            
            logger.info(f"User {user_id} registered successfully")
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "email": email,
                "roles": roles
            }
            
        except Exception as e:
            logger.error(f"User registration error: {e}")
            return {
                "success": False,
                "error": "Registration failed due to internal error"
            }
    
    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        user_repository  # 実際のユーザーリポジトリ
    ) -> Dict[str, Any]:
        """
        パスワード変更
        
        Args:
            user_id: ユーザーID
            current_password: 現在のパスワード
            new_password: 新しいパスワード
            user_repository: ユーザーリポジトリ
            
        Returns:
            変更結果
        """
        try:
            # ユーザー情報取得
            user_data = self._get_user_by_id(user_id, user_repository)
            if not user_data:
                return {"success": False, "error": "User not found"}
            
            # 現在のパスワード検証
            if not self.password_handler.verify_password(
                current_password, user_data["password_hash"]
            ):
                return {"success": False, "error": "Current password is incorrect"}
            
            # 新しいパスワード強度チェック
            if not self.password_handler.is_password_secure(new_password):
                strength_info = self.password_handler.check_password_strength(new_password)
                return {
                    "success": False,
                    "error": "New password is not secure enough",
                    "password_issues": strength_info["issues"],
                    "suggestions": strength_info["suggestions"]
                }
            
            # パスワード更新
            new_password_hash = self.password_handler.hash_password(new_password)
            self._update_user_password(user_id, new_password_hash, user_repository)
            
            logger.info(f"Password changed for user {user_id}")
            
            return {"success": True, "message": "Password changed successfully"}
            
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return {"success": False, "error": "Password change failed"}
    
    def _get_user_by_username_or_email(self, username_or_email: str, user_repository):
        """ユーザー名またはメールでユーザーを検索（実装例）"""
        # 実際の実装では user_repository を使用
        # ここではダミーデータを返す
        return {
            "user_id": "user_123",
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "$2b$12$example_hash",
            "is_active": True
        }
    
    def _get_user_by_id(self, user_id: str, user_repository):
        """ユーザーIDでユーザーを検索（実装例）"""
        # 実際の実装では user_repository を使用
        return {
            "user_id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "$2b$12$example_hash",
            "is_active": True
        }
    
    def _user_exists(self, username: str, email: str, user_repository) -> bool:
        """ユーザー存在チェック（実装例）"""
        # 実際の実装では user_repository を使用
        return False
    
    def _create_user(self, username: str, email: str, password_hash: str, user_repository) -> str:
        """ユーザー作成（実装例）"""
        # 実際の実装では user_repository を使用
        return f"user_{username}_{datetime.now().timestamp()}"
    
    def _update_last_login(self, user_id: str, user_repository):
        """最終ログイン時刻更新（実装例）"""
        # 実際の実装では user_repository を使用
        pass
    
    def _update_user_password(self, user_id: str, password_hash: str, user_repository):
        """ユーザーパスワード更新（実装例）"""
        # 実際の実装では user_repository を使用
        pass
    
    def _is_account_locked(self, username_or_email: str) -> bool:
        """アカウントロック状態チェック"""
        if username_or_email not in self._failed_login_attempts:
            return False
        
        attempts = self._failed_login_attempts[username_or_email]
        if len(attempts) < self.max_failed_attempts:
            return False
        
        # 最新の失敗時刻から lockout_duration_minutes 経過していればロック解除
        latest_attempt = max(attempts)
        lockout_until = latest_attempt + timedelta(minutes=self.lockout_duration_minutes)
        
        if datetime.now(timezone.utc) > lockout_until:
            # ロック期間終了、失敗記録をクリア
            del self._failed_login_attempts[username_or_email]
            return False
        
        return True
    
    def _record_failed_attempt(self, username_or_email: str):
        """ログイン失敗記録"""
        if username_or_email not in self._failed_login_attempts:
            self._failed_login_attempts[username_or_email] = []
        
        self._failed_login_attempts[username_or_email].append(
            datetime.now(timezone.utc)
        )
        
        # 古い記録を削除（24時間以上前）
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._failed_login_attempts[username_or_email] = [
            attempt for attempt in self._failed_login_attempts[username_or_email]
            if attempt > cutoff
        ]
    
    def _clear_failed_attempts(self, username_or_email: str):
        """ログイン失敗記録をクリア"""
        if username_or_email in self._failed_login_attempts:
            del self._failed_login_attempts[username_or_email]
    
    def _create_session(self, user_id: str, access_token: str) -> str:
        """セッション作成"""
        session_id = f"session_{user_id}_{datetime.now().timestamp()}"
        
        self._active_sessions[user_id] = {
            "session_id": session_id,
            "access_token": access_token,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        
        return session_id
    
    def _remove_session(self, user_id: str):
        """セッション削除"""
        if user_id in self._active_sessions:
            del self._active_sessions[user_id]
    
    def _is_session_valid(self, user_id: str) -> bool:
        """セッション有効性チェック"""
        if user_id not in self._active_sessions:
            return False
        
        session = self._active_sessions[user_id]
        
        # セッションタイムアウトチェック
        timeout = session["last_activity"] + timedelta(hours=self.session_timeout_hours)
        
        if datetime.now(timezone.utc) > timeout:
            # セッション期限切れ
            del self._active_sessions[user_id]
            return False
        
        # 最終活動時刻を更新
        session["last_activity"] = datetime.now(timezone.utc)
        return True