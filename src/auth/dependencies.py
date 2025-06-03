"""
FastAPI依存性注入

認証、権限チェック、現在ユーザー取得などのFastAPI依存性を提供します。
"""

from typing import Optional, List, Annotated
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .jwt_handler import JWTHandler
from .auth_service import AuthService, AuthUser
from .permissions import PermissionManager, Permission, Role
from .security import SecurityManager
from ..config.auth_config import get_auth_settings
from ..repositories.user_repository import UserRepository
from ..services.user_service import UserService

logger = logging.getLogger(__name__)

# セキュリティスキーム
security = HTTPBearer()


# === 基本的な依存性 ===

def get_jwt_handler() -> JWTHandler:
    """JWTハンドラーを取得"""
    settings = get_auth_settings()
    return JWTHandler(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days
    )


def get_permission_manager() -> PermissionManager:
    """権限マネージャーを取得"""
    return PermissionManager()


def get_security_manager() -> SecurityManager:
    """セキュリティマネージャーを取得"""
    return SecurityManager()


def get_user_repository() -> UserRepository:
    """ユーザーリポジトリを取得"""
    # 実際の実装では、データベース接続マネージャーを注入
    return UserRepository(connection_manager=None)


def get_auth_service(
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    permission_manager: PermissionManager = Depends(get_permission_manager),
    user_repository: UserRepository = Depends(get_user_repository)
) -> AuthService:
    """認証サービスを取得"""
    from .password_handler import PasswordHandler
    password_handler = PasswordHandler()
    
    return AuthService(
        jwt_handler=jwt_handler,
        password_handler=password_handler,
        permission_manager=permission_manager
    )


def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
    auth_service: AuthService = Depends(get_auth_service),
    permission_manager: PermissionManager = Depends(get_permission_manager)
) -> UserService:
    """ユーザーサービスを取得"""
    return UserService(
        user_repository=user_repository,
        auth_service=auth_service,
        permission_manager=permission_manager
    )


# === 認証関連の依存性 ===

async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    ヘッダーからトークンを取得
    
    Args:
        credentials: HTTP認証クレデンシャル
        
    Returns:
        アクセストークン
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_token_from_header),
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthUser:
    """
    現在のユーザーを取得
    
    Args:
        token: アクセストークン
        auth_service: 認証サービス
        
    Returns:
        認証ユーザー
        
    Raises:
        HTTPException: 認証に失敗した場合
    """
    try:
        user = auth_service.validate_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """
    現在のアクティブユーザーを取得
    
    Args:
        current_user: 現在のユーザー
        
    Returns:
        アクティブユーザー
        
    Raises:
        HTTPException: ユーザーが非アクティブな場合
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return current_user


async def get_optional_current_user(
    token: Optional[str] = Depends(get_token_from_header),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[AuthUser]:
    """
    現在のユーザーを取得（オプション）
    
    Args:
        token: アクセストークン（オプション）
        auth_service: 認証サービス
        
    Returns:
        認証ユーザー、または None
    """
    if not token:
        return None
    
    try:
        return auth_service.validate_token(token)
    except Exception:
        return None


# === 権限チェック依存性 ===

def require_permission(permission: Permission):
    """
    特定の権限を要求する依存性を作成
    
    Args:
        permission: 必要な権限
        
    Returns:
        依存性関数
    """
    async def check_permission(
        current_user: AuthUser = Depends(get_current_active_user),
        permission_manager: PermissionManager = Depends(get_permission_manager)
    ) -> AuthUser:
        if not permission_manager.has_permission(current_user.user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required"
            )
        return current_user
    
    return check_permission


def require_any_permission(*permissions: Permission):
    """
    いずれかの権限を要求する依存性を作成
    
    Args:
        permissions: 必要な権限のリスト
        
    Returns:
        依存性関数
    """
    async def check_any_permission(
        current_user: AuthUser = Depends(get_current_active_user),
        permission_manager: PermissionManager = Depends(get_permission_manager)
    ) -> AuthUser:
        if not permission_manager.has_any_permission(current_user.user_id, list(permissions)):
            permission_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permission_names)}"
            )
        return current_user
    
    return check_any_permission


def require_all_permissions(*permissions: Permission):
    """
    全ての権限を要求する依存性を作成
    
    Args:
        permissions: 必要な権限のリスト
        
    Returns:
        依存性関数
    """
    async def check_all_permissions(
        current_user: AuthUser = Depends(get_current_active_user),
        permission_manager: PermissionManager = Depends(get_permission_manager)
    ) -> AuthUser:
        if not permission_manager.has_all_permissions(current_user.user_id, list(permissions)):
            permission_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"All of these permissions required: {', '.join(permission_names)}"
            )
        return current_user
    
    return check_all_permissions


def require_role(role: Role):
    """
    特定のロールを要求する依存性を作成
    
    Args:
        role: 必要なロール
        
    Returns:
        依存性関数
    """
    async def check_role(
        current_user: AuthUser = Depends(get_current_active_user),
        permission_manager: PermissionManager = Depends(get_permission_manager)
    ) -> AuthUser:
        if not permission_manager.has_role(current_user.user_id, role.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' required"
            )
        return current_user
    
    return check_role


def require_any_role(*roles: Role):
    """
    いずれかのロールを要求する依存性を作成
    
    Args:
        roles: 必要なロールのリスト
        
    Returns:
        依存性関数
    """
    async def check_any_role(
        current_user: AuthUser = Depends(get_current_active_user),
        permission_manager: PermissionManager = Depends(get_permission_manager)
    ) -> AuthUser:
        role_names = [role.value for role in roles]
        user_roles = permission_manager.get_user_roles(current_user.user_id)
        
        if not any(role in user_roles for role in role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(role_names)}"
            )
        return current_user
    
    return check_any_role


# === セキュリティ関連の依存性 ===

async def check_rate_limit(
    request: Request,
    endpoint: str,
    security_manager: SecurityManager = Depends(get_security_manager),
    current_user: Optional[AuthUser] = Depends(get_optional_current_user)
):
    """
    レート制限をチェック
    
    Args:
        request: HTTPリクエスト
        endpoint: エンドポイント名
        security_manager: セキュリティマネージャー
        current_user: 現在のユーザー（オプション）
        
    Raises:
        HTTPException: レート制限に達した場合
    """
    client_ip = request.client.host if request.client else "unknown"
    user_id = current_user.user_id if current_user else None
    
    allowed, error_message = security_manager.check_rate_limit(
        client_ip=client_ip,
        endpoint=endpoint,
        user_id=user_id
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_message or "Rate limit exceeded"
        )


async def get_client_info(request: Request) -> dict:
    """
    クライアント情報を取得
    
    Args:
        request: HTTPリクエスト
        
    Returns:
        クライアント情報
    """
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "referer": request.headers.get("referer"),
        "origin": request.headers.get("origin")
    }


async def validate_csrf_token(
    request: Request,
    csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token"),
    security_manager: SecurityManager = Depends(get_security_manager)
):
    """
    CSRFトークンを検証
    
    Args:
        request: HTTPリクエスト
        csrf_token: CSRFトークン
        security_manager: セキュリティマネージャー
        
    Raises:
        HTTPException: CSRFトークンが無効な場合
    """
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token required"
            )
        
        # セッショントークンを取得（実際の実装では適切に取得）
        session_token = "dummy_session_token"
        
        if not security_manager.validate_csrf_token(csrf_token, session_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )


# === 便利な依存性 ===

# 管理者ユーザー
AdminUser = Annotated[AuthUser, Depends(require_any_role(Role.ADMIN, Role.SUPER_ADMIN))]

# 読み取り権限ユーザー
ReadUser = Annotated[AuthUser, Depends(require_permission(Permission.API_ACCESS))]

# ユーザー管理権限ユーザー
UserManagerUser = Annotated[AuthUser, Depends(require_permission(Permission.USER_UPDATE))]

# 顧客管理権限ユーザー
CustomerManagerUser = Annotated[AuthUser, Depends(require_permission(Permission.CUSTOMER_UPDATE))]

# 商品管理権限ユーザー
ProductManagerUser = Annotated[AuthUser, Depends(require_permission(Permission.PRODUCT_UPDATE))]

# 分析権限ユーザー
AnalystUser = Annotated[AuthUser, Depends(require_permission(Permission.ANALYTICS_READ))]


# === 特殊な依存性 ===

def require_owner_or_permission(permission: Permission):
    """
    リソースの所有者または特定の権限を要求する依存性を作成
    
    Args:
        permission: 必要な権限
        
    Returns:
        依存性関数
    """
    async def check_owner_or_permission(
        resource_user_id: str,  # リソースの所有者ID
        current_user: AuthUser = Depends(get_current_active_user),
        permission_manager: PermissionManager = Depends(get_permission_manager)
    ) -> AuthUser:
        # 所有者チェック
        if current_user.user_id == resource_user_id:
            return current_user
        
        # 権限チェック
        if permission_manager.has_permission(current_user.user_id, permission):
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resource owner access or specific permission required"
        )
    
    return check_owner_or_permission


async def get_pagination_params(
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100
) -> dict:
    """
    ページネーションパラメータを取得
    
    Args:
        page: ページ番号
        per_page: ページあたりのアイテム数
        max_per_page: 最大ページあたりのアイテム数
        
    Returns:
        ページネーションパラメータ
        
    Raises:
        HTTPException: パラメータが無効な場合
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be greater than 0"
        )
    
    if per_page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per page must be greater than 0"
        )
    
    if per_page > max_per_page:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Per page must not exceed {max_per_page}"
        )
    
    return {
        "page": page,
        "per_page": per_page,
        "offset": (page - 1) * per_page
    }


async def get_sort_params(
    sort_by: str = "created_at",
    sort_order: str = "desc",
    allowed_fields: List[str] = None
) -> dict:
    """
    ソートパラメータを取得
    
    Args:
        sort_by: ソートフィールド
        sort_order: ソート順序
        allowed_fields: 許可されたフィールド
        
    Returns:
        ソートパラメータ
        
    Raises:
        HTTPException: パラメータが無効な場合
    """
    if allowed_fields and sort_by not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sort field must be one of: {', '.join(allowed_fields)}"
        )
    
    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sort order must be 'asc' or 'desc'"
        )
    
    return {
        "sort_by": sort_by,
        "sort_order": sort_order
    }