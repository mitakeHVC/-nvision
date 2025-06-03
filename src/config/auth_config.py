"""
認証設定

JWT設定、セキュリティ設定、認証設定を管理します。
"""

import os
import secrets
from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from datetime import timedelta


class AuthSettings(BaseSettings):
    """認証設定"""
    
    # JWT設定
    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT署名用の秘密鍵"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT署名アルゴリズム"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="アクセストークンの有効期限（分）"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="リフレッシュトークンの有効期限（日）"
    )
    
    # パスワード設定
    password_min_length: int = Field(
        default=8,
        description="パスワードの最小長"
    )
    password_require_uppercase: bool = Field(
        default=True,
        description="大文字を必須とするか"
    )
    password_require_lowercase: bool = Field(
        default=True,
        description="小文字を必須とするか"
    )
    password_require_digits: bool = Field(
        default=True,
        description="数字を必須とするか"
    )
    password_require_symbols: bool = Field(
        default=True,
        description="記号を必須とするか"
    )
    password_hash_rounds: int = Field(
        default=12,
        description="bcryptのハッシュラウンド数"
    )
    
    # セキュリティ設定
    max_failed_login_attempts: int = Field(
        default=5,
        description="最大ログイン失敗回数"
    )
    account_lockout_duration_minutes: int = Field(
        default=15,
        description="アカウントロック期間（分）"
    )
    session_timeout_hours: int = Field(
        default=24,
        description="セッションタイムアウト（時間）"
    )
    max_sessions_per_user: int = Field(
        default=5,
        description="ユーザーあたりの最大セッション数"
    )
    
    # 二要素認証設定
    enable_two_factor: bool = Field(
        default=False,
        description="二要素認証を有効にするか"
    )
    totp_issuer: str = Field(
        default="nvision",
        description="TOTPの発行者名"
    )
    backup_codes_count: int = Field(
        default=10,
        description="バックアップコードの数"
    )
    
    # メール認証設定
    enable_email_verification: bool = Field(
        default=True,
        description="メール認証を有効にするか"
    )
    email_verification_expire_hours: int = Field(
        default=24,
        description="メール認証の有効期限（時間）"
    )
    
    # パスワードリセット設定
    password_reset_expire_hours: int = Field(
        default=1,
        description="パスワードリセットの有効期限（時間）"
    )
    password_reset_max_attempts: int = Field(
        default=3,
        description="パスワードリセットの最大試行回数"
    )
    
    # レート制限設定
    rate_limit_enabled: bool = Field(
        default=True,
        description="レート制限を有効にするか"
    )
    login_rate_limit_requests: int = Field(
        default=5,
        description="ログインのレート制限（リクエスト数）"
    )
    login_rate_limit_window_minutes: int = Field(
        default=5,
        description="ログインのレート制限（時間窓：分）"
    )
    api_rate_limit_requests: int = Field(
        default=100,
        description="APIのレート制限（リクエスト数）"
    )
    api_rate_limit_window_minutes: int = Field(
        default=1,
        description="APIのレート制限（時間窓：分）"
    )
    
    # CORS設定
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="許可するCORSオリジン"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="CORSでクレデンシャルを許可するか"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="許可するHTTPメソッド"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="許可するHTTPヘッダー"
    )
    
    # セキュリティヘッダー設定
    security_headers_enabled: bool = Field(
        default=True,
        description="セキュリティヘッダーを有効にするか"
    )
    content_security_policy: str = Field(
        default=(
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        ),
        description="Content Security Policy"
    )
    
    # ログ設定
    log_security_events: bool = Field(
        default=True,
        description="セキュリティイベントをログに記録するか"
    )
    log_failed_logins: bool = Field(
        default=True,
        description="ログイン失敗をログに記録するか"
    )
    log_successful_logins: bool = Field(
        default=True,
        description="ログイン成功をログに記録するか"
    )
    
    # 開発・デバッグ設定
    debug_mode: bool = Field(
        default=False,
        description="デバッグモードを有効にするか"
    )
    allow_insecure_passwords: bool = Field(
        default=False,
        description="安全でないパスワードを許可するか（開発用）"
    )
    disable_rate_limiting: bool = Field(
        default=False,
        description="レート制限を無効にするか（開発用）"
    )
    
    @validator('jwt_secret_key')
    def validate_jwt_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters long')
        return v
    
    @validator('password_min_length')
    def validate_password_min_length(cls, v):
        if v < 6:
            raise ValueError('Password minimum length must be at least 6')
        return v
    
    @validator('password_hash_rounds')
    def validate_password_hash_rounds(cls, v):
        if v < 10 or v > 15:
            raise ValueError('Password hash rounds must be between 10 and 15')
        return v
    
    class Config:
        env_prefix = "AUTH_"
        env_file = ".env"
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """セキュリティ設定"""
    
    # ブルートフォース攻撃対策
    enable_brute_force_protection: bool = Field(
        default=True,
        description="ブルートフォース攻撃対策を有効にするか"
    )
    suspicious_activity_threshold: int = Field(
        default=10,
        description="疑わしい活動の閾値"
    )
    auto_block_suspicious_ips: bool = Field(
        default=True,
        description="疑わしいIPを自動ブロックするか"
    )
    block_duration_hours: int = Field(
        default=1,
        description="ブロック期間（時間）"
    )
    
    # セッションセキュリティ
    enable_session_security: bool = Field(
        default=True,
        description="セッションセキュリティを有効にするか"
    )
    session_ip_validation: bool = Field(
        default=True,
        description="セッションのIP検証を行うか"
    )
    session_user_agent_validation: bool = Field(
        default=True,
        description="セッションのユーザーエージェント検証を行うか"
    )
    
    # CSRF保護
    enable_csrf_protection: bool = Field(
        default=True,
        description="CSRF保護を有効にするか"
    )
    csrf_token_expire_minutes: int = Field(
        default=60,
        description="CSRFトークンの有効期限（分）"
    )
    
    # データ保護
    enable_data_encryption: bool = Field(
        default=True,
        description="データ暗号化を有効にするか"
    )
    encryption_key: Optional[str] = Field(
        default=None,
        description="データ暗号化キー"
    )
    
    # 監査ログ
    enable_audit_logging: bool = Field(
        default=True,
        description="監査ログを有効にするか"
    )
    audit_log_retention_days: int = Field(
        default=365,
        description="監査ログの保持期間（日）"
    )
    
    # プライバシー設定
    data_retention_days: int = Field(
        default=365,
        description="データ保持期間（日）"
    )
    enable_gdpr_compliance: bool = Field(
        default=True,
        description="GDPR準拠を有効にするか"
    )
    
    class Config:
        env_prefix = "SECURITY_"
        env_file = ".env"
        case_sensitive = False


class DatabaseSettings(BaseSettings):
    """データベース設定（認証関連）"""
    
    # 接続設定
    auth_database_url: str = Field(
        default="sqlite:///./auth.db",
        description="認証データベースURL"
    )
    auth_database_pool_size: int = Field(
        default=10,
        description="データベース接続プールサイズ"
    )
    auth_database_max_overflow: int = Field(
        default=20,
        description="データベース接続プール最大オーバーフロー"
    )
    
    # Redis設定（セッション・キャッシュ用）
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="RedisサーバーURL"
    )
    redis_session_db: int = Field(
        default=1,
        description="セッション用Redisデータベース番号"
    )
    redis_cache_db: int = Field(
        default=2,
        description="キャッシュ用Redisデータベース番号"
    )
    
    class Config:
        env_prefix = "AUTH_DB_"
        env_file = ".env"
        case_sensitive = False


class EmailSettings(BaseSettings):
    """メール設定"""
    
    # SMTP設定
    smtp_server: str = Field(
        default="localhost",
        description="SMTPサーバー"
    )
    smtp_port: int = Field(
        default=587,
        description="SMTPポート"
    )
    smtp_username: Optional[str] = Field(
        default=None,
        description="SMTP認証ユーザー名"
    )
    smtp_password: Optional[str] = Field(
        default=None,
        description="SMTP認証パスワード"
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="SMTP TLSを使用するか"
    )
    
    # メール設定
    from_email: str = Field(
        default="noreply@nvision.com",
        description="送信者メールアドレス"
    )
    from_name: str = Field(
        default="nvision",
        description="送信者名"
    )
    
    # テンプレート設定
    email_templates_dir: str = Field(
        default="templates/email",
        description="メールテンプレートディレクトリ"
    )
    
    class Config:
        env_prefix = "EMAIL_"
        env_file = ".env"
        case_sensitive = False


# 設定インスタンス
auth_settings = AuthSettings()
security_settings = SecuritySettings()
database_settings = DatabaseSettings()
email_settings = EmailSettings()


def get_auth_settings() -> AuthSettings:
    """認証設定を取得"""
    return auth_settings


def get_security_settings() -> SecuritySettings:
    """セキュリティ設定を取得"""
    return security_settings


def get_database_settings() -> DatabaseSettings:
    """データベース設定を取得"""
    return database_settings


def get_email_settings() -> EmailSettings:
    """メール設定を取得"""
    return email_settings


# 設定検証
def validate_settings():
    """設定を検証"""
    errors = []
    
    # JWT秘密鍵の検証
    if len(auth_settings.jwt_secret_key) < 32:
        errors.append("JWT secret key is too short")
    
    # パスワード設定の検証
    if auth_settings.password_min_length < 6:
        errors.append("Password minimum length is too short")
    
    # セキュリティ設定の検証
    if not security_settings.enable_brute_force_protection and not auth_settings.debug_mode:
        errors.append("Brute force protection should be enabled in production")
    
    if not security_settings.enable_csrf_protection and not auth_settings.debug_mode:
        errors.append("CSRF protection should be enabled in production")
    
    # 本番環境での設定チェック
    if not auth_settings.debug_mode:
        if auth_settings.allow_insecure_passwords:
            errors.append("Insecure passwords should not be allowed in production")
        
        if auth_settings.disable_rate_limiting:
            errors.append("Rate limiting should not be disabled in production")
        
        if auth_settings.jwt_secret_key == "your-secret-key":
            errors.append("Default JWT secret key should not be used in production")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")


# 初期化時に設定を検証
try:
    validate_settings()
except ValueError as e:
    if not auth_settings.debug_mode:
        raise e
    else:
        print(f"Warning: {e}")