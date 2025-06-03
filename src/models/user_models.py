"""
ユーザーモデル

ユーザー関連のPydanticモデルを定義します。
"""

from typing import Optional, List, Dict, Any
import uuid # Added import for uuid
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserCreate(BaseModel):
    """ユーザー作成"""
    username: str = Field(..., description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., description="パスワード")
    first_name: str = Field(..., description="名")
    last_name: str = Field(..., description="姓")


class UserUpdate(BaseModel):
    """ユーザー更新"""
    first_name: Optional[str] = Field(None, description="名")
    last_name: Optional[str] = Field(None, description="姓")
    email: Optional[EmailStr] = Field(None, description="メールアドレス")


class User(BaseModel):
    """ユーザー"""
    id: int = Field(..., description="ユーザーID")
    username: str = Field(..., description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    first_name: str = Field(..., description="名")
    last_name: str = Field(..., description="姓")
    is_active: bool = Field(default=True, description="アクティブ状態")
    created_at: Optional[datetime] = Field(None, description="作成日時")
    updated_at: Optional[datetime] = Field(None, description="更新日時")


class UserInDB(User):
    """データベース内のユーザーモデル"""
    hashed_password: str = Field(..., description="ハッシュ化されたパスワード")
    # Add any other fields that are in the DB but not necessarily in the basic User model
    # For example, roles, permissions directly stored, etc.
    # For now, keeping it simple.


class UserProfile(BaseModel):
    """ユーザープロフィール"""
    id: int = Field(..., description="ユーザーID")
    username: str = Field(..., description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    first_name: str = Field(..., description="名")
    last_name: str = Field(..., description="姓")
    full_name: Optional[str] = Field(None, description="フルネーム")
    avatar_url: Optional[str] = Field(None, description="アバターURL")
    bio: Optional[str] = Field(None, description="自己紹介")
    location: Optional[str] = Field(None, description="所在地")
    website: Optional[str] = Field(None, description="ウェブサイト")


class UserProfileUpdate(BaseModel):
    """ユーザープロフィール更新"""
    first_name: Optional[str] = Field(None, description="名")
    last_name: Optional[str] = Field(None, description="姓")
    bio: Optional[str] = Field(None, description="自己紹介")
    location: Optional[str] = Field(None, description="所在地")
    website: Optional[str] = Field(None, description="ウェブサイト")


class UserPreferences(BaseModel):
    """ユーザー設定"""
    theme: str = Field(default="light", description="テーマ")
    language: str = Field(default="ja", description="言語")
    timezone: str = Field(default="Asia/Tokyo", description="タイムゾーン")
    notifications: bool = Field(default=True, description="通知設定")
    email_notifications: bool = Field(default=True, description="メール通知")
    marketing_emails: bool = Field(default=False, description="マーケティングメール")


class UserPreferencesUpdate(BaseModel):
    """ユーザー設定更新"""
    theme: Optional[str] = Field(None, description="テーマ")
    language: Optional[str] = Field(None, description="言語")
    timezone: Optional[str] = Field(None, description="タイムゾーン")
    notifications: Optional[bool] = Field(None, description="通知設定")
    email_notifications: Optional[bool] = Field(None, description="メール通知")
    marketing_emails: Optional[bool] = Field(None, description="マーケティングメール")


class UserDashboardData(BaseModel):
    """ユーザーダッシュボードデータ"""
    user: UserProfile = Field(..., description="ユーザープロフィール")
    preferences: UserPreferences = Field(..., description="ユーザー設定")
    stats: Optional[dict] = Field(None, description="統計情報")
    recent_activity: Optional[List[dict]] = Field(None, description="最近のアクティビティ")


class UsernameAvailabilityRequest(BaseModel):
    """ユーザー名利用可能性チェックリクエスト"""
    username: str = Field(..., description="ユーザー名")


class EmailAvailabilityRequest(BaseModel):
    """メールアドレス利用可能性チェックリクエスト"""
    email: EmailStr = Field(..., description="メールアドレス")


class AvailabilityResponse(BaseModel):
    """利用可能性チェックレスポンス"""
    available: bool = Field(..., description="利用可能かどうか")
    message: str = Field(..., description="メッセージ")
    suggestions: Optional[List[str]] = Field(None, description="代替案")


# Models that were missing, based on UserRepository imports:

class UserActivity(BaseModel):
    activity_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="アクティビティID")
    user_id: int # Or str, depending on User.id type. Assuming int from User model.
    activity_type: str = Field(..., description="アクティビティタイプ (例: login, item_purchase)")
    details: Optional[Dict[str, Any]] = Field(None, description="アクティビティ詳細")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserStats(BaseModel):
    user_id: int # Or str
    total_logins: int = 0
    total_orders: int = 0
    total_spend: float = 0.0
    last_active_at: Optional[datetime] = None
    # other stats fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserRole(BaseModel):
    role_id: str = Field(..., description="ロールID")
    role_name: str = Field(..., description="ロール名")
    # permissions: List[str] = [] # Or link to UserPermission model

class UserPermission(BaseModel):
    permission_id: str = Field(..., description="権限ID")
    permission_name: str = Field(..., description="権限名 (例: user:create)")
    description: Optional[str] = None

class UserGroup(BaseModel):
    group_id: str = Field(..., description="グループID")
    group_name: str = Field(..., description="グループ名")
    members: List[int] = [] # List of user_ids or User model

class UserDevice(BaseModel):
    device_id: str = Field(..., description="デバイスID")
    user_id: int # Or str
    device_type: str = Field(..., description="例: mobile, web, desktop")
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class UserNotification(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="通知ID")
    user_id: int # Or str
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # type: str (e.g., 'alert', 'info', 'promo')

class UserApiKey(BaseModel):
    key_id: str = Field(..., description="APIキーID")
    user_id: int # Or str
    api_key_hash: str # Store hash, not the key itself
    label: Optional[str] = None
    scopes: List[str] = [] # e.g. ['read:data', 'write:data']
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

class UserAuditLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ログID")
    user_id: int # Or str, acting user
    action: str = Field(..., description="実行されたアクション (例: user_update, item_delete)")
    resource: Optional[str] = Field(None, description="影響を受けたリソースタイプ (例: user, product)")
    resource_id: Optional[str] = Field(None, description="影響を受けたリソースID")
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True # Was the action successful?

class UserSearchRequest(BaseModel):
    query: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    sort_by: str = "created_at"
    sort_order: str = "desc" # "asc" or "desc"
    page: int = 1
    per_page: int = 20