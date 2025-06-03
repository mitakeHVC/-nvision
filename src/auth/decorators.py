"""
認証デコレータ

認証デコレータ、権限チェックデコレータ、ロールベースアクセス制御を提供します。
"""

import functools
from typing import List, Optional, Callable, Any, Union
from fastapi import HTTPException, status
import logging

from .permissions import Permission, Role, PermissionManager
from .auth_service import AuthService

logger = logging.getLogger(__name__)


def require_auth(func: Callable) -> Callable:
    """
    認証が必要な関数に適用するデコレータ
    
    Args:
        func: デコレートする関数
        
    Returns:
        デコレートされた関数
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 実際の実装では、リクエストから認証情報を取得して検証
        # ここではダミー実装
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Authentication required for {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    
    return wrapper


def require_permissions(*permissions: Permission):
    """
    特定の権限が必要な関数に適用するデコレータ
    
    Args:
        permissions: 必要な権限のリスト
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、現在のユーザーの権限をチェック
            # ここではダミー実装
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Permission check failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        
        # メタデータとして権限情報を保存
        wrapper._required_permissions = permissions
        return wrapper
    
    return decorator


def require_roles(*roles: Union[str, Role]):
    """
    特定のロールが必要な関数に適用するデコレータ
    
    Args:
        roles: 必要なロールのリスト
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、現在のユーザーのロールをチェック
            # ここではダミー実装
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Role check failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient role privileges"
                )
        
        # メタデータとしてロール情報を保存
        role_names = []
        for role in roles:
            if isinstance(role, Role):
                role_names.append(role.value)
            else:
                role_names.append(role)
        wrapper._required_roles = role_names
        return wrapper
    
    return decorator


def require_any_permission(*permissions: Permission):
    """
    指定された権限のいずれかが必要な関数に適用するデコレータ
    
    Args:
        permissions: 必要な権限のリスト（いずれか一つ）
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、現在のユーザーがいずれかの権限を持っているかチェック
            # ここではダミー実装
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Any permission check failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="At least one of the required permissions is needed"
                )
        
        wrapper._required_any_permissions = permissions
        return wrapper
    
    return decorator


def require_any_role(*roles: Union[str, Role]):
    """
    指定されたロールのいずれかが必要な関数に適用するデコレータ
    
    Args:
        roles: 必要なロールのリスト（いずれか一つ）
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、現在のユーザーがいずれかのロールを持っているかチェック
            # ここではダミー実装
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Any role check failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="At least one of the required roles is needed"
                )
        
        role_names = []
        for role in roles:
            if isinstance(role, Role):
                role_names.append(role.value)
            else:
                role_names.append(role)
        wrapper._required_any_roles = role_names
        return wrapper
    
    return decorator


def require_owner_or_permission(permission: Permission):
    """
    リソースの所有者または特定の権限が必要な関数に適用するデコレータ
    
    Args:
        permission: 必要な権限
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、リソースの所有者チェックまたは権限チェック
            # ここではダミー実装
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Owner or permission check failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Resource owner access or specific permission required"
                )
        
        wrapper._required_owner_or_permission = permission
        return wrapper
    
    return decorator


def rate_limit(max_requests: int, window_seconds: int):
    """
    レート制限デコレータ
    
    Args:
        max_requests: 最大リクエスト数
        window_seconds: 時間窓（秒）
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、レート制限をチェック
            # ここではダミー実装
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Rate limit check failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
        
        wrapper._rate_limit = {"max_requests": max_requests, "window_seconds": window_seconds}
        return wrapper
    
    return decorator


def audit_log(action: str, resource: str):
    """
    監査ログデコレータ
    
    Args:
        action: アクション名
        resource: リソース名
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 実際の実装では、監査ログを記録
            logger.info(f"Audit log: {action} on {resource} by function {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                logger.info(f"Audit log: {action} on {resource} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Audit log: {action} on {resource} failed: {e}")
                raise
        
        wrapper._audit_log = {"action": action, "resource": resource}
        return wrapper
    
    return decorator


def cache_result(ttl_seconds: int = 300):
    """
    結果キャッシュデコレータ
    
    Args:
        ttl_seconds: キャッシュの生存時間（秒）
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 簡単なキャッシュ実装（実際の実装ではRedisなどを使用）
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            if cache_key in cache:
                cached_result, timestamp = cache[cache_key]
                if (timestamp + ttl_seconds) > time.time():
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
                else:
                    del cache[cache_key]
            
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            
            return result
        
        wrapper._cache_ttl = ttl_seconds
        return wrapper
    
    return decorator


def validate_input(validator_func: Callable):
    """
    入力検証デコレータ
    
    Args:
        validator_func: 検証関数
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 入力検証
            try:
                validator_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Input validation failed for {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Input validation failed: {str(e)}"
                )
            
            return await func(*args, **kwargs)
        
        wrapper._input_validator = validator_func
        return wrapper
    
    return decorator


def handle_exceptions(*exception_types):
    """
    例外処理デコレータ
    
    Args:
        exception_types: 処理する例外タイプ
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exception_types as e:
                logger.error(f"Handled exception in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )
            except Exception as e:
                logger.error(f"Unhandled exception in {func.__name__}: {e}")
                raise
        
        wrapper._handled_exceptions = exception_types
        return wrapper
    
    return decorator


# 複合デコレータ
def secure_endpoint(
    permissions: Optional[List[Permission]] = None,
    roles: Optional[List[Union[str, Role]]] = None,
    rate_limit_requests: Optional[int] = None,
    rate_limit_window: Optional[int] = None,
    audit_action: Optional[str] = None,
    audit_resource: Optional[str] = None
):
    """
    セキュアなエンドポイント用の複合デコレータ
    
    Args:
        permissions: 必要な権限
        roles: 必要なロール
        rate_limit_requests: レート制限のリクエスト数
        rate_limit_window: レート制限の時間窓
        audit_action: 監査ログのアクション
        audit_resource: 監査ログのリソース
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        # 認証を適用
        decorated_func = require_auth(func)
        
        # 権限チェックを適用
        if permissions:
            decorated_func = require_permissions(*permissions)(decorated_func)
        
        # ロールチェックを適用
        if roles:
            decorated_func = require_roles(*roles)(decorated_func)
        
        # レート制限を適用
        if rate_limit_requests and rate_limit_window:
            decorated_func = rate_limit(rate_limit_requests, rate_limit_window)(decorated_func)
        
        # 監査ログを適用
        if audit_action and audit_resource:
            decorated_func = audit_log(audit_action, audit_resource)(decorated_func)
        
        return decorated_func
    
    return decorator


# 管理者専用デコレータ
def admin_only(func: Callable) -> Callable:
    """管理者専用デコレータ"""
    return secure_endpoint(
        roles=[Role.ADMIN, Role.SUPER_ADMIN],
        audit_action="admin_action",
        audit_resource="admin_resource"
    )(func)


# 読み取り専用デコレータ
def read_only(resource: str):
    """読み取り専用デコレータ"""
    def decorator(func: Callable) -> Callable:
        return secure_endpoint(
            permissions=[Permission.API_ACCESS],
            rate_limit_requests=100,
            rate_limit_window=60,
            audit_action="read",
            audit_resource=resource
        )(func)
    return decorator


# 書き込み権限デコレータ
def write_access(resource: str, permission: Permission):
    """書き込み権限デコレータ"""
    def decorator(func: Callable) -> Callable:
        return secure_endpoint(
            permissions=[permission],
            rate_limit_requests=50,
            rate_limit_window=60,
            audit_action="write",
            audit_resource=resource
        )(func)
    return decorator


import time  # time モジュールをインポート