"""
JWT トークン生成・検証ハンドラー

JWTトークンの生成、検証、リフレッシュ機能を提供します。
"""

import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """トークンデータモデル"""
    user_id: str
    username: str
    email: str
    roles: list[str]
    permissions: list[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID


class JWTHandler:
    """JWT トークンハンドラー"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        """
        JWTハンドラーを初期化
        
        Args:
            secret_key: JWT署名用の秘密鍵
            algorithm: 署名アルゴリズム
            access_token_expire_minutes: アクセストークンの有効期限（分）
            refresh_token_expire_days: リフレッシュトークンの有効期限（日）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        
        # トークンブラックリスト（実際の実装ではRedisなどを使用）
        self._blacklisted_tokens: set[str] = set()
    
    def create_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: list[str],
        permissions: list[str],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        アクセストークンを生成
        
        Args:
            user_id: ユーザーID
            username: ユーザー名
            email: メールアドレス
            roles: ユーザーロール
            permissions: ユーザー権限
            expires_delta: カスタム有効期限
            
        Returns:
            JWT アクセストークン
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": user_id,  # subject
            "username": username,
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": "access"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Access token created for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise
    
    def create_refresh_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        リフレッシュトークンを生成
        
        Args:
            user_id: ユーザーID
            expires_delta: カスタム有効期限
            
        Returns:
            JWT リフレッシュトークン
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.refresh_token_expire_days
            )
        
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": "refresh"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Refresh token created for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        トークンを検証
        
        Args:
            token: JWT トークン
            
        Returns:
            デコードされたペイロード、または None（無効な場合）
        """
        try:
            # ブラックリストチェック
            if self._is_token_blacklisted(token):
                logger.warning("Blacklisted token used")
                return None
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # 有効期限チェック
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                logger.warning("Expired token used")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def get_token_data(self, token: str) -> Optional[TokenData]:
        """
        トークンからTokenDataオブジェクトを取得
        
        Args:
            token: JWT トークン
            
        Returns:
            TokenData オブジェクト、または None（無効な場合）
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        try:
            return TokenData(
                user_id=payload["sub"],
                username=payload.get("username", ""),
                email=payload.get("email", ""),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                exp=datetime.fromtimestamp(payload["exp"], timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], timezone.utc),
                jti=payload["jti"]
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse token data: {e}")
            return None
    
    def refresh_access_token(
        self,
        refresh_token: str,
        user_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        リフレッシュトークンを使用してアクセストークンを更新
        
        Args:
            refresh_token: リフレッシュトークン
            user_data: ユーザーデータ（roles, permissionsなど）
            
        Returns:
            新しいアクセストークン、または None（無効な場合）
        """
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning("Invalid refresh token")
            return None
        
        try:
            return self.create_access_token(
                user_id=payload["sub"],
                username=user_data.get("username", ""),
                email=user_data.get("email", ""),
                roles=user_data.get("roles", []),
                permissions=user_data.get("permissions", [])
            )
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None
    
    def blacklist_token(self, token: str) -> bool:
        """
        トークンをブラックリストに追加
        
        Args:
            token: ブラックリストに追加するトークン
            
        Returns:
            成功した場合 True
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # 期限切れでもJTIを取得
            )
            jti = payload.get("jti")
            if jti:
                self._blacklisted_tokens.add(jti)
                logger.info(f"Token {jti} added to blacklist")
                return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
        
        return False
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """
        トークンがブラックリストに含まれているかチェック
        
        Args:
            token: チェックするトークン
            
        Returns:
            ブラックリストに含まれている場合 True
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            jti = payload.get("jti")
            return jti in self._blacklisted_tokens
        except Exception:
            return True  # デコードできない場合は無効とみなす
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        トークンの有効期限を取得
        
        Args:
            token: JWT トークン
            
        Returns:
            有効期限、または None（無効な場合）
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, timezone.utc)
        
        return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        トークンが期限切れかチェック
        
        Args:
            token: JWT トークン
            
        Returns:
            期限切れの場合 True
        """
        expiry = self.get_token_expiry(token)
        if not expiry:
            return True
        
        return expiry < datetime.now(timezone.utc)