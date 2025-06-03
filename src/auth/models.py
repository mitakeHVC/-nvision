"""
認証モデル

認証関連のPydanticモデルを定義します。
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    username_or_email: str = Field(..., description="ユーザー名またはメールアドレス")
    password: str = Field(..., description="パスワード")


class LoginResponse(BaseModel):
    """ログインレスポンス"""
    access_token: str = Field(..., description="アクセストークン")
    refresh_token: str = Field(..., description="リフレッシュトークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="有効期限（秒）")
    user: dict = Field(..., description="ユーザー情報")


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエスト"""
    refresh_token: str = Field(..., description="リフレッシュトークン")


class RefreshTokenResponse(BaseModel):
    """リフレッシュトークンレスポンス"""
    access_token: str = Field(..., description="新しいアクセストークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="有効期限（秒）")


class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエスト"""
    current_password: str = Field(..., description="現在のパスワード")
    new_password: str = Field(..., description="新しいパスワード")
    confirm_password: str = Field(..., description="新しいパスワード（確認）")


class PasswordResetRequest(BaseModel):
    """パスワードリセットリクエスト"""
    email: EmailStr = Field(..., description="メールアドレス")


class PasswordResetConfirm(BaseModel):
    """パスワードリセット確認"""
    token: str = Field(..., description="リセットトークン")
    new_password: str = Field(..., description="新しいパスワード")
    confirm_password: str = Field(..., description="新しいパスワード（確認）")


from datetime import datetime # Added for LoginAttempt and SecurityEvent

class LoginAttempt(BaseModel):
    """ログイン試行モデル"""
    attempt_id: str # Should be populated, e.g. uuid
    username: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    successful: bool
    # Additional details like reason for failure, etc. could be added

class SecurityEvent(BaseModel):
    """セキュリティイベントモデル"""
    event_id: str # Should be populated, e.g. uuid
    event_type: str # e.g., "password_reset_request", "failed_login_limit_exceeded"
    user_id: Optional[str] = None # Associated user if applicable
    ip_address: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
