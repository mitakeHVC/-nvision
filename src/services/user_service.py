"""
ユーザーサービス（ダミー実装）

実際の運用フローテスト用のダミーユーザーサービスです。
"""

from typing import Optional, Dict, Any


class UserService:
    """ユーザーサービス（ダミー実装）"""
    
    async def register_user(self, user_data):
        """ユーザー登録"""
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
        """ユーザーIDでユーザーを取得"""
        return {
            "id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True
        }
    
    async def get_user_by_email(self, email: str):
        """メールアドレスでユーザーを取得"""
        return {
            "id": 1,
            "username": "testuser",
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "is_active": True
        }
    
    async def change_password(self, user_id: int, password_request):
        """パスワード変更"""
        return {"success": True}
    
    async def update_user(self, user_id: int, user_data, updated_by: int):
        """ユーザー更新"""
        return {
            "id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "is_active": True
        }
    
    async def get_user_dashboard_data(self, user_id: int):
        """ユーザーダッシュボードデータを取得"""
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
        """ユーザー名の利用可能性をチェック"""
        return username != "admin"
    
    async def check_email_availability(self, email: str):
        """メールアドレスの利用可能性をチェック"""
        return email != "admin@example.com"