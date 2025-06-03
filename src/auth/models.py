"""
認証関連モデル

ユーザー、ロール、権限、トークンなどの認証関連データモデルを定義します。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


class UserStatus(str, Enum):
    """ユーザーステータス"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class TokenType(str, Enum):
    """トークンタイプ"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFICATION = "verification"


# === 基本モデル ===

class UserBase(BaseModel):
    """ユーザー基本モデル"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('Username must contain only alphanumeric characters, underscores, or hyphens')
        return v.lower()


class UserCreate(UserBase):
    """ユーザー作成モデル"""
    password: str = Field(..., min_length=8)
    confirm_password: str
    roles: Optional[List[str]] = Field(default_factory=lambda: ["viewer"])
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseModel):
    """ユーザー更新モデル"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None


class UserInDB(UserBase):
    """データベース内ユーザーモデル"""
    user_id: str
    password_hash: str
    status: UserStatus = UserStatus.ACTIVE
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    last_failed_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None


class User(UserBase):
    """公開ユーザーモデル"""
    user_id: str
    status: UserStatus
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    
    class Config:
        from_attributes = True


# === 認証関連モデル ===

class LoginRequest(BaseModel):
    """ログインリクエストモデル"""
    username_or_email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class LoginResponse(BaseModel):
    """ログインレスポンスモデル"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class TokenData(BaseModel):
    """トークンデータモデル"""
    user_id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    token_type: TokenType
    expires_at: datetime
    issued_at: datetime
    jti: str  # JWT ID


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエストモデル"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """リフレッシュトークンレスポンスモデル"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# === パスワード関連モデル ===

class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエストモデル"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordResetRequest(BaseModel):
    """パスワードリセットリクエストモデル"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """パスワードリセット確認モデル"""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordStrength(BaseModel):
    """パスワード強度モデル"""
    score: int = Field(..., ge=0, le=5)
    strength: str
    length: int
    has_lowercase: bool
    has_uppercase: bool
    has_digits: bool
    has_symbols: bool
    character_types: int
    issues: List[str]
    suggestions: List[str]


# === ロール・権限関連モデル ===

class RoleBase(BaseModel):
    """ロール基本モデル"""
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., max_length=200)
    permissions: List[str] = Field(default_factory=list)


class RoleCreate(RoleBase):
    """ロール作成モデル"""
    inherits_from: Optional[List[str]] = None


class RoleUpdate(BaseModel):
    """ロール更新モデル"""
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None
    inherits_from: Optional[List[str]] = None


class Role(RoleBase):
    """ロールモデル"""
    role_id: str
    created_at: datetime
    updated_at: datetime
    is_system_role: bool = False
    
    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """権限基本モデル"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=200)
    resource: str = Field(..., max_length=50)
    action: str = Field(..., max_length=50)


class Permission(PermissionBase):
    """権限モデル"""
    permission_id: str
    created_at: datetime
    is_system_permission: bool = False
    
    class Config:
        from_attributes = True


# === セッション関連モデル ===

class SessionData(BaseModel):
    """セッションデータモデル"""
    session_id: str
    user_id: str
    client_ip: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool = True


class ActiveSession(BaseModel):
    """アクティブセッションモデル"""
    session_id: str
    client_ip: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    is_current: bool = False


# === セキュリティ関連モデル ===

class SecurityEvent(BaseModel):
    """セキュリティイベントモデル"""
    event_id: str
    event_type: str
    user_id: Optional[str] = None
    client_ip: str
    user_agent: Optional[str] = None
    timestamp: datetime
    details: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical


class LoginAttempt(BaseModel):
    """ログイン試行モデル"""
    attempt_id: str
    username_or_email: str
    client_ip: str
    user_agent: Optional[str] = None
    success: bool
    failure_reason: Optional[str] = None
    timestamp: datetime


class RateLimitInfo(BaseModel):
    """レート制限情報モデル"""
    endpoint: str
    max_requests: int
    window_seconds: int
    current_requests: int
    reset_time: datetime
    blocked: bool = False


# === API レスポンスモデル ===

class ApiResponse(BaseModel):
    """API レスポンス基本モデル"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class UserListResponse(BaseModel):
    """ユーザーリストレスポンスモデル"""
    users: List[User]
    total: int
    page: int
    per_page: int
    pages: int


class RoleListResponse(BaseModel):
    """ロールリストレスポンスモデル"""
    roles: List[Role]
    total: int


class PermissionListResponse(BaseModel):
    """権限リストレスポンスモデル"""
    permissions: List[Permission]
    total: int


class SecurityStatsResponse(BaseModel):
    """セキュリティ統計レスポンスモデル"""
    active_sessions: int
    blocked_clients: int
    suspicious_ips: int
    recent_events_24h: int
    event_types: Dict[str, int]
    failed_attempts: int
    last_cleanup: str


# === バリデーション関連モデル ===

class EmailVerificationRequest(BaseModel):
    """メール認証リクエストモデル"""
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    """メール認証確認モデル"""
    token: str


class TwoFactorSetupRequest(BaseModel):
    """二要素認証設定リクエストモデル"""
    password: str


class TwoFactorConfirmRequest(BaseModel):
    """二要素認証確認リクエストモデル"""
    code: str
    backup_code: Optional[str] = None


class TwoFactorLoginRequest(BaseModel):
    """二要素認証ログインリクエストモデル"""
    username_or_email: str
    password: str
    totp_code: Optional[str] = None
    backup_code: Optional[str] = None


# === 設定関連モデル ===

class AuthConfig(BaseModel):
    """認証設定モデル"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_symbols: bool = True
    max_failed_login_attempts: int = 5
    account_lockout_duration_minutes: int = 15
    session_timeout_hours: int = 24
    enable_two_factor: bool = False
    enable_email_verification: bool = True
    rate_limit_enabled: bool = True


class SecurityConfig(BaseModel):
    """セキュリティ設定モデル"""
    enable_rate_limiting: bool = True
    enable_brute_force_protection: bool = True
    enable_session_security: bool = True
    enable_csrf_protection: bool = True
    max_sessions_per_user: int = 5
    suspicious_activity_threshold: int = 10
    security_headers_enabled: bool = True
    log_security_events: bool = True