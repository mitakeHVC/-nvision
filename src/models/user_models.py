"""
ユーザーモデル

ユーザー関連のPydanticモデルを定義します。
"""

from typing import Optional, List
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