"""
認証ルーター

ログイン、ログアウト、ユーザー登録、パスワード変更・リセット、プロフィール管理、トークンリフレッシュのエンドポイントを提供します。
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse

from ..exceptions import (
    AuthenticationError, AuthorizationError, ValidationError,
    NotFoundError, ConflictError, handle_exceptions
)
from ..dependencies import (
    get_auth_service, get_user_service, get_security_manager,
    get_current_user, get_current_active_user, get_client_info,
    check_rate_limit
)
from ...auth.models import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm
)
from ...models.user_models import (
    UserCreate, User, UserProfile, UserProfileUpdate,
    UserPreferences, UserPreferencesUpdate, UserDashboardData,
    UsernameAvailabilityRequest, EmailAvailabilityRequest, AvailabilityResponse
)
from ...auth.auth_service import AuthService, AuthUser
from ...services.user_service import UserService
from ...auth.security import SecurityManager

router = APIRouter()
security = HTTPBearer()


# === 認証エンドポイント ===

@router.post("/login", response_model=LoginResponse, summary="ユーザーログイン")
@handle_exceptions("Login failed")
async def login(
    login_request: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    security_manager: SecurityManager = Depends(get_security_manager),
    client_info: dict = Depends(get_client_info)
):
    """
    ユーザーログイン
    
    Args:
        login_request: ログインリクエスト
        request: HTTPリクエスト
        auth_service: 認証サービス
        security_manager: セキュリティマネージャー
        client_info: クライアント情報
        
    Returns:
        ログインレスポンス（アクセストークン、リフレッシュトークン、ユーザー情報）
        
    Raises:
        AuthenticationError: 認証に失敗した場合
        RateLimitError: レート制限に達した場合
    """
    # レート制限チェック
    await check_rate_limit(request, "login")
    
    # 認証実行
    result = await auth_service.authenticate_user(
        username_or_email=login_request.username_or_email,
        password=login_request.password,
        user_repository=auth_service.user_repository
    )
    
    if not result.success:
        # ログイン失敗を記録
        security_manager.record_failed_login(
            client_info["ip"],
            login_request.username_or_email
        )
        
        raise AuthenticationError(
            message=result.error_message or "Authentication failed",
            details={"username_or_email": login_request.username_or_email}
        )
    
    # ログイン成功時の処理
    security_manager.clear_failed_attempts(
        client_info["ip"],
        login_request.username_or_email
    )
    
    # セッション作成
    session_token = security_manager.create_secure_session(
        user_id=result.user_id,
        client_ip=client_info["ip"],
        user_agent=client_info["user_agent"]
    )
    
    # ユーザー情報を取得
    user_service: UserService = Depends(get_user_service)
    user = await user_service.get_user_by_id(result.user_id)
    
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="bearer",
        expires_in=auth_service.jwt_handler.access_token_expire_minutes * 60,
        user=user
    )


@router.post("/logout", summary="ユーザーログアウト")
@handle_exceptions("Logout failed")
async def logout(
    current_user: AuthUser = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
    security_manager: SecurityManager = Depends(get_security_manager)
):
    """
    ユーザーログアウト
    
    Args:
        current_user: 現在のユーザー
        auth_service: 認証サービス
        security_manager: セキュリティマネージャー
        
    Returns:
        ログアウト結果
    """
    # トークンを無効化
    # 実際の実装では、リクエストからトークンを取得
    access_token = "dummy_token"  # 実際の実装で修正
    
    success = auth_service.logout_user(access_token, current_user.user_id)
    
    if not success:
        raise AuthenticationError("Logout failed")
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=RefreshTokenResponse, summary="トークンリフレッシュ")
@handle_exceptions("Token refresh failed")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    アクセストークンをリフレッシュ
    
    Args:
        refresh_request: リフレッシュトークンリクエスト
        auth_service: 認証サービス
        
    Returns:
        新しいアクセストークン
        
    Raises:
        AuthenticationError: リフレッシュトークンが無効な場合
    """
    new_access_token = auth_service.refresh_token(
        refresh_token=refresh_request.refresh_token,
        user_repository=auth_service.user_repository
    )
    
    if not new_access_token:
        raise AuthenticationError("Invalid or expired refresh token")
    
    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=auth_service.jwt_handler.access_token_expire_minutes * 60
    )


# === ユーザー登録エンドポイント ===

@router.post("/register", response_model=User, summary="ユーザー登録")
@handle_exceptions("User registration failed")
async def register_user(
    user_data: UserCreate,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    client_info: dict = Depends(get_client_info)
):
    """
    新規ユーザー登録
    
    Args:
        user_data: ユーザー作成データ
        request: HTTPリクエスト
        user_service: ユーザーサービス
        client_info: クライアント情報
        
    Returns:
        作成されたユーザー情報
        
    Raises:
        ValidationError: バリデーションエラー
        ConflictError: ユーザー名またはメールが既に存在する場合
    """
    # レート制限チェック
    await check_rate_limit(request, "register")
    
    # ユーザー登録
    result = await user_service.register_user(user_data)
    
    if not result["success"]:
        if "already exists" in result.get("error", ""):
            raise ConflictError(result["error"])
        else:
            raise ValidationError(
                message=result.get("error", "Registration failed"),
                details=result.get("password_issues")
            )
    
    return result["user"]


# === パスワード管理エンドポイント ===

@router.post("/change-password", summary="パスワード変更")
@handle_exceptions("Password change failed")
async def change_password(
    password_request: PasswordChangeRequest,
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    パスワード変更
    
    Args:
        password_request: パスワード変更リクエスト
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        変更結果
        
    Raises:
        ValidationError: パスワードが無効な場合
        AuthenticationError: 現在のパスワードが間違っている場合
    """
    result = await user_service.change_password(
        user_id=current_user.user_id,
        password_request=password_request
    )
    
    if not result["success"]:
        if "incorrect" in result.get("error", "").lower():
            raise AuthenticationError(result["error"])
        else:
            raise ValidationError(
                message=result.get("error", "Password change failed"),
                details=result.get("password_issues")
            )
    
    return {"message": "Password changed successfully"}


@router.post("/password-reset", summary="パスワードリセット要求")
@handle_exceptions("Password reset request failed")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    パスワードリセット要求
    
    Args:
        reset_request: パスワードリセットリクエスト
        request: HTTPリクエスト
        user_service: ユーザーサービス
        
    Returns:
        リセット要求結果
    """
    # レート制限チェック
    await check_rate_limit(request, "password_reset")
    
    # 実際の実装では、メール送信処理を行う
    # ここではダミー実装
    user = await user_service.get_user_by_email(reset_request.email)
    
    # セキュリティのため、ユーザーが存在しない場合でも成功レスポンスを返す
    return {
        "message": "If the email address exists, a password reset link has been sent"
    }


@router.post("/password-reset/confirm", summary="パスワードリセット確認")
@handle_exceptions("Password reset confirmation failed")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    user_service: UserService = Depends(get_user_service)
):
    """
    パスワードリセット確認
    
    Args:
        reset_confirm: パスワードリセット確認データ
        user_service: ユーザーサービス
        
    Returns:
        リセット確認結果
        
    Raises:
        AuthenticationError: トークンが無効な場合
        ValidationError: パスワードが無効な場合
    """
    # 実際の実装では、トークンを検証してパスワードを更新
    # ここではダミー実装
    
    # トークン検証（実装例）
    # if not validate_reset_token(reset_confirm.token):
    #     raise AuthenticationError("Invalid or expired reset token")
    
    return {"message": "Password reset successfully"}


# === プロフィール管理エンドポイント ===

@router.get("/profile", response_model=UserProfile, summary="プロフィール取得")
@handle_exceptions("Failed to get profile")
async def get_profile(
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    現在のユーザーのプロフィールを取得
    
    Args:
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        ユーザープロフィール
    """
    dashboard_data = await user_service.get_user_dashboard_data(current_user.user_id)
    
    if not dashboard_data:
        raise NotFoundError("User profile not found")
    
    return dashboard_data.user


@router.put("/profile", response_model=UserProfile, summary="プロフィール更新")
@handle_exceptions("Failed to update profile")
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    プロフィールを更新
    
    Args:
        profile_update: プロフィール更新データ
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        更新されたプロフィール
        
    Raises:
        ValidationError: バリデーションエラー
    """
    # UserUpdateに変換
    from ...models.user_models import UserUpdate
    user_update = UserUpdate(
        first_name=profile_update.first_name,
        last_name=profile_update.last_name
    )
    
    updated_user = await user_service.update_user(
        user_id=current_user.user_id,
        user_data=user_update,
        updated_by=current_user.user_id
    )
    
    if not updated_user:
        raise ValidationError("Failed to update profile")
    
    # 更新されたプロフィールを取得
    dashboard_data = await user_service.get_user_dashboard_data(current_user.user_id)
    return dashboard_data.user


@router.get("/preferences", response_model=UserPreferences, summary="設定取得")
@handle_exceptions("Failed to get preferences")
async def get_preferences(
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    ユーザー設定を取得
    
    Args:
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        ユーザー設定
    """
    dashboard_data = await user_service.get_user_dashboard_data(current_user.user_id)
    
    if not dashboard_data:
        raise NotFoundError("User preferences not found")
    
    return dashboard_data.preferences


@router.put("/preferences", response_model=UserPreferences, summary="設定更新")
@handle_exceptions("Failed to update preferences")
async def update_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    ユーザー設定を更新
    
    Args:
        preferences_update: 設定更新データ
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        更新された設定
    """
    # 実際の実装では、設定を更新
    # ここではダミー実装
    dashboard_data = await user_service.get_user_dashboard_data(current_user.user_id)
    return dashboard_data.preferences


@router.get("/dashboard", response_model=UserDashboardData, summary="ダッシュボードデータ取得")
@handle_exceptions("Failed to get dashboard data")
async def get_dashboard_data(
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    ダッシュボードデータを取得
    
    Args:
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        ダッシュボードデータ
    """
    dashboard_data = await user_service.get_user_dashboard_data(current_user.user_id)
    
    if not dashboard_data:
        raise NotFoundError("Dashboard data not found")
    
    return dashboard_data


# === ユーザー情報確認エンドポイント ===

@router.get("/me", response_model=User, summary="現在のユーザー情報取得")
@handle_exceptions("Failed to get current user")
async def get_current_user_info(
    current_user: AuthUser = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    現在のユーザー情報を取得
    
    Args:
        current_user: 現在のユーザー
        user_service: ユーザーサービス
        
    Returns:
        現在のユーザー情報
    """
    user = await user_service.get_user_by_id(current_user.user_id)
    
    if not user:
        raise NotFoundError("User not found")
    
    return user


# === 利用可能性チェックエンドポイント ===

@router.post("/check-username", response_model=AvailabilityResponse, summary="ユーザー名利用可能性チェック")
@handle_exceptions("Username availability check failed")
async def check_username_availability(
    request_data: UsernameAvailabilityRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    ユーザー名の利用可能性をチェック
    
    Args:
        request_data: ユーザー名チェックリクエスト
        user_service: ユーザーサービス
        
    Returns:
        利用可能性チェック結果
    """
    available = await user_service.check_username_availability(request_data.username)
    
    return AvailabilityResponse(
        available=available,
        message="Username is available" if available else "Username is already taken",
        suggestions=[] if available else [f"{request_data.username}1", f"{request_data.username}_user"]
    )


@router.post("/check-email", response_model=AvailabilityResponse, summary="メールアドレス利用可能性チェック")
@handle_exceptions("Email availability check failed")
async def check_email_availability(
    request_data: EmailAvailabilityRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    メールアドレスの利用可能性をチェック
    
    Args:
        request_data: メールアドレスチェックリクエスト
        user_service: ユーザーサービス
        
    Returns:
        利用可能性チェック結果
    """
    available = await user_service.check_email_availability(request_data.email)
    
    return AvailabilityResponse(
        available=available,
        message="Email is available" if available else "Email is already registered"
    )


# === CSRFトークンエンドポイント ===

@router.get("/csrf-token", summary="CSRFトークン取得")
async def get_csrf_token(
    current_user: AuthUser = Depends(get_current_active_user),
    security_manager: SecurityManager = Depends(get_security_manager)
):
    """
    CSRFトークンを取得
    
    Args:
        current_user: 現在のユーザー
        security_manager: セキュリティマネージャー
        
    Returns:
        CSRFトークン
    """
    # セッショントークンを取得（実際の実装では適切に取得）
    session_token = "dummy_session_token"
    
    csrf_token = security_manager.generate_csrf_token(session_token)
    
    return {
        "csrf_token": csrf_token,
        "expires_in": 3600  # 1時間
    }