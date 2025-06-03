"""
API依存関係

FastAPIの依存関係注入で使用される関数を定義します。
"""

from typing import Dict, Any
from fastapi import Request, HTTPException, status
import time


# ダミー実装 - 実際の運用フローテスト用
async def get_auth_service():
    """認証サービスを取得（ダミー実装）"""
    class DummyAuthService:
        def __init__(self):
            self.jwt_handler = type('obj', (object,), {'access_token_expire_minutes': 30})()
            self.user_repository = None
            
        async def authenticate_user(self, username_or_email: str, password: str, user_repository=None):
            # テスト用のダミー認証
            if username_or_email == "test@example.com" and password == "password123":
                return type('obj', (object,), {
                    'success': True,
                    'user_id': 1,
                    'access_token': 'dummy_access_token',
                    'refresh_token': 'dummy_refresh_token'
                })()
            return type('obj', (object,), {'success': False, 'error_message': 'Invalid credentials'})()
            
        def logout_user(self, access_token: str, user_id: int):
            return True
            
        def refresh_token(self, refresh_token: str, user_repository=None):
            return "new_dummy_access_token"
    
    return DummyAuthService()


async def get_user_service():
    """ユーザーサービスを取得（ダミー実装）"""
    class DummyUserService:
        async def register_user(self, user_data):
            return {
                "success": True,
                "user": {
                    "id": 1,
                    "username": user_data.username,
                    "email": user_data.email,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "is_active": True
                }
            }
            
        async def get_user_by_id(self, user_id: int):
            return {
                "id": user_id,
                "username": "testuser",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "is_active": True
            }
            
        async def get_user_by_email(self, email: str):
            return {
                "id": 1,
                "username": "testuser",
                "email": email,
                "first_name": "Test",
                "last_name": "User",
                "is_active": True
            }
            
        async def change_password(self, user_id: int, password_request):
            return {"success": True}
            
        async def update_user(self, user_id: int, user_data, updated_by: int):
            return {
                "id": user_id,
                "username": "testuser",
                "email": "test@example.com",
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "is_active": True
            }
            
        async def get_user_dashboard_data(self, user_id: int):
            return type('obj', (object,), {
                'user': {
                    "id": user_id,
                    "username": "testuser",
                    "email": "test@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "is_active": True
                },
                'preferences': {
                    "theme": "light",
                    "language": "ja",
                    "notifications": True
                }
            })()
            
        async def check_username_availability(self, username: str):
            return username != "admin"
            
        async def check_email_availability(self, email: str):
            return email != "admin@example.com"
    
    return DummyUserService()


async def get_security_manager():
    """セキュリティマネージャーを取得（ダミー実装）"""
    class DummySecurityManager:
        def record_failed_login(self, ip: str, username: str):
            pass
            
        def clear_failed_attempts(self, ip: str, username: str):
            pass
            
        def create_secure_session(self, user_id: int, client_ip: str, user_agent: str):
            return "dummy_session_token"
            
        def generate_csrf_token(self, session_token: str):
            return "dummy_csrf_token"
    
    return DummySecurityManager()


async def get_current_user():
    """現在のユーザーを取得（ダミー実装）"""
    return type('obj', (object,), {
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'is_active': True
    })()


async def get_current_active_user():
    """現在のアクティブユーザーを取得（ダミー実装）"""
    return await get_current_user()


async def get_client_info(request: Request):
    """クライアント情報を取得"""
    return {
        "ip": request.client.host if request.client else "127.0.0.1",
        "user_agent": request.headers.get("user-agent", "Unknown")
    }


# レート制限チェック（ダミー実装）
_rate_limit_store = {}

async def check_rate_limit(request: Request, endpoint: str):
    """レート制限をチェック"""
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = f"{client_ip}:{endpoint}"
    current_time = time.time()
    
    if key in _rate_limit_store:
        last_request_time = _rate_limit_store[key]
        if current_time - last_request_time < 1:  # 1秒間隔制限
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
    
    _rate_limit_store[key] = current_time