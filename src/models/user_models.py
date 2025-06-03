"""
ユーザー管理モデル

ユーザー、ロール、権限、認証トークンなどのPydanticモデルを定義します。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

# 認証モデルから基本クラスをインポート
from ..auth.models import (
    UserBase, UserCreate, UserUpdate, UserInDB, User,
    LoginRequest, LoginResponse, TokenData,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    RoleBase, RoleCreate, RoleUpdate, Role,
    PermissionBase, Permission,
    SessionData, ActiveSession,
    SecurityEvent, LoginAttempt
)


class UserProfile(BaseModel):
    """ユーザープロフィールモデル"""
    user_id: str
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en"
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    email_verified: bool = False
    
    @validator('full_name', always=True)
    def generate_full_name(cls, v, values):
        if v:
            return v
        first_name = values.get('first_name', '')
        last_name = values.get('last_name', '')
        if first_name and last_name:
            return f"{first_name} {last_name}"
        return first_name or last_name or None


class UserProfileUpdate(BaseModel):
    """ユーザープロフィール更新モデル"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPreferences(BaseModel):
    """ユーザー設定モデル"""
    user_id: str
    theme: str = "light"  # light, dark, auto
    language: str = "en"
    timezone: str = "UTC"
    email_notifications: bool = True
    push_notifications: bool = True
    marketing_emails: bool = False
    two_factor_enabled: bool = False
    session_timeout: int = 24  # hours
    auto_logout: bool = True
    privacy_level: str = "normal"  # minimal, normal, full
    data_retention_days: int = 365
    created_at: datetime
    updated_at: datetime


class UserPreferencesUpdate(BaseModel):
    """ユーザー設定更新モデル"""
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    session_timeout: Optional[int] = Field(None, ge=1, le=168)  # 1-168 hours
    auto_logout: Optional[bool] = None
    privacy_level: Optional[str] = None
    data_retention_days: Optional[int] = Field(None, ge=30, le=2555)  # 30 days - 7 years


class UserActivity(BaseModel):
    """ユーザー活動モデル"""
    activity_id: str
    user_id: str
    activity_type: str  # login, logout, password_change, profile_update, etc.
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserStats(BaseModel):
    """ユーザー統計モデル"""
    user_id: str
    total_logins: int = 0
    last_login: Optional[datetime] = None
    login_streak: int = 0
    failed_login_attempts: int = 0
    password_changes: int = 0
    profile_updates: int = 0
    sessions_created: int = 0
    api_calls_today: int = 0
    api_calls_total: int = 0
    created_at: datetime
    updated_at: datetime


class UserRole(BaseModel):
    """ユーザーロール関連モデル"""
    user_id: str
    role_id: str
    role_name: str
    assigned_at: datetime
    assigned_by: str
    expires_at: Optional[datetime] = None
    is_active: bool = True


class UserPermission(BaseModel):
    """ユーザー権限関連モデル"""
    user_id: str
    permission_id: str
    permission_name: str
    granted_at: datetime
    granted_by: str
    expires_at: Optional[datetime] = None
    is_active: bool = True


class UserGroup(BaseModel):
    """ユーザーグループモデル"""
    group_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: str
    member_count: int = 0


class UserGroupMembership(BaseModel):
    """ユーザーグループメンバーシップモデル"""
    user_id: str
    group_id: str
    joined_at: datetime
    role_in_group: str = "member"  # member, admin, owner
    is_active: bool = True


class UserDevice(BaseModel):
    """ユーザーデバイスモデル"""
    device_id: str
    user_id: str
    device_name: str
    device_type: str  # mobile, desktop, tablet
    os: Optional[str] = None
    browser: Optional[str] = None
    ip_address: str
    location: Optional[str] = None
    is_trusted: bool = False
    last_used: datetime
    created_at: datetime


class UserNotification(BaseModel):
    """ユーザー通知モデル"""
    notification_id: str
    user_id: str
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    notification_type: str  # info, warning, error, success
    priority: str = "normal"  # low, normal, high, urgent
    is_read: bool = False
    is_archived: bool = False
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    read_at: Optional[datetime] = None


class UserApiKey(BaseModel):
    """ユーザーAPIキーモデル"""
    key_id: str
    user_id: str
    name: str = Field(..., max_length=100)
    key_hash: str
    permissions: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None  # requests per hour
    is_active: bool = True
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    created_at: datetime
    usage_count: int = 0


class UserBackupCode(BaseModel):
    """ユーザーバックアップコードモデル（2FA用）"""
    code_id: str
    user_id: str
    code_hash: str
    is_used: bool = False
    used_at: Optional[datetime] = None
    created_at: datetime


class UserAuditLog(BaseModel):
    """ユーザー監査ログモデル"""
    log_id: str
    user_id: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None


# === リクエスト/レスポンスモデル ===

class UserSearchRequest(BaseModel):
    """ユーザー検索リクエストモデル"""
    query: Optional[str] = None
    roles: Optional[List[str]] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_login_after: Optional[datetime] = None
    last_login_before: Optional[datetime] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = "desc"


class UserSearchResponse(BaseModel):
    """ユーザー検索レスポンスモデル"""
    users: List[User]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


class UserRoleAssignmentRequest(BaseModel):
    """ユーザーロール割り当てリクエストモデル"""
    user_id: str
    role_names: List[str]
    expires_at: Optional[datetime] = None


class UserPermissionGrantRequest(BaseModel):
    """ユーザー権限付与リクエストモデル"""
    user_id: str
    permission_names: List[str]
    expires_at: Optional[datetime] = None


class BulkUserActionRequest(BaseModel):
    """一括ユーザー操作リクエストモデル"""
    user_ids: List[str] = Field(..., min_items=1, max_items=100)
    action: str  # activate, deactivate, delete, assign_role, remove_role
    parameters: Optional[Dict[str, Any]] = None


class UserExportRequest(BaseModel):
    """ユーザーエクスポートリクエストモデル"""
    format: str = "csv"  # csv, json, xlsx
    fields: Optional[List[str]] = None
    filters: Optional[UserSearchRequest] = None
    include_sensitive: bool = False


class UserImportRequest(BaseModel):
    """ユーザーインポートリクエストモデル"""
    format: str = "csv"  # csv, json, xlsx
    data: str  # Base64 encoded file content
    update_existing: bool = False
    send_welcome_email: bool = True
    default_roles: List[str] = Field(default_factory=lambda: ["viewer"])


class UserDashboardData(BaseModel):
    """ユーザーダッシュボードデータモデル"""
    user: UserProfile
    stats: UserStats
    recent_activities: List[UserActivity]
    active_sessions: List[ActiveSession]
    notifications: List[UserNotification]
    api_keys: List[UserApiKey]
    preferences: UserPreferences


class AdminUserOverview(BaseModel):
    """管理者用ユーザー概要モデル"""
    total_users: int
    active_users: int
    inactive_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    users_by_role: Dict[str, int]
    recent_registrations: List[User]
    recent_logins: List[UserActivity]
    security_alerts: List[SecurityEvent]


# === バリデーション用モデル ===

class UsernameAvailabilityRequest(BaseModel):
    """ユーザー名利用可能性チェックリクエストモデル"""
    username: str = Field(..., min_length=3, max_length=50)


class EmailAvailabilityRequest(BaseModel):
    """メールアドレス利用可能性チェックリクエストモデル"""
    email: EmailStr


class AvailabilityResponse(BaseModel):
    """利用可能性チェックレスポンスモデル"""
    available: bool
    message: str
    suggestions: Optional[List[str]] = None


# === 設定モデル ===

class UserManagementConfig(BaseModel):
    """ユーザー管理設定モデル"""
    allow_self_registration: bool = True
    require_email_verification: bool = True
    default_user_role: str = "viewer"
    max_users: Optional[int] = None
    username_min_length: int = 3
    username_max_length: int = 50
    password_min_length: int = 8
    session_timeout_hours: int = 24
    max_sessions_per_user: int = 5
    enable_user_profiles: bool = True
    enable_user_preferences: bool = True
    enable_api_keys: bool = True
    enable_audit_logging: bool = True
    data_retention_days: int = 365