"""
認証サービス（ダミー実装）

実際の運用フローテスト用のダミー認証サービスです。
"""

from typing import Optional


class AuthUser:
    """認証ユーザー"""
    def __init__(self, user_id: int, username: str, email: str, is_active: bool = True):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.is_active = is_active


class AuthService:
    """認証サービス（ダミー実装）"""
    
    def __init__(self):
        self.jwt_handler = type('obj', (object,), {'access_token_expire_minutes': 30})()
        self.user_repository = None
    
    async def authenticate_user(self, username_or_email: str, password: str, user_repository=None):
        """ユーザー認証"""
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
        """ユーザーログアウト"""
        return True
    
    def refresh_token(self, refresh_token: str, user_repository=None):
        """トークンリフレッシュ"""
        return "new_dummy_access_token"