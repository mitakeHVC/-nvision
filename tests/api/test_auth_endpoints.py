"""
認証エンドポイントテスト

認証・認可システムのエンドポイントテストを提供します。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.main import app # Corrected import
from src.auth.models import LoginRequest # Corrected import
from src.models.user_models import User, UserCreate # Corrected import, UserCreate was missing from this import line


class TestAuthEndpoints:
    """認証エンドポイントテストクラス"""
    
    @pytest.fixture
    def client(self):
        """テストクライアントを作成"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_data(self):
        """モックユーザーデータ"""
        return {
            "user_id": "test_user_123",
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
            "roles": ["viewer"],
            "permissions": ["api:access"],
            "created_at": "2024-01-01T00:00:00Z",
            "status": "active",
            "email_verified": True
        }
    
    @pytest.fixture
    def mock_login_response(self):
        """モックログインレスポンス"""
        return {
            "success": True,
            "user_id": "test_user_123",
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_at": "2024-01-01T01:00:00Z",
            "user_data": {
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["viewer"],
                "permissions": ["api:access"]
            }
        }
    
    # === ログインテスト ===
    
    def test_login_success(self, client, mock_login_response, mock_user_data):
        """ログイン成功テスト"""
        with patch('src.auth.auth_service.AuthService.authenticate_user') as mock_auth, \
             patch('src.services.user_service.UserService.get_user_by_id') as mock_get_user:
            
            # モック設定
            mock_auth.return_value = Mock(**mock_login_response)
            mock_get_user.return_value = User(**mock_user_data)
            
            # リクエスト実行
            response = client.post(
                "/auth/login",
                json={
                    "username_or_email": "testuser",
                    "password": "testpassword"
                }
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
    
    def test_login_invalid_credentials(self, client):
        """ログイン失敗テスト（無効な認証情報）"""
        with patch('src.auth.auth_service.AuthService.authenticate_user') as mock_auth:
            
            # モック設定（認証失敗）
            mock_auth.return_value = Mock(
                success=False,
                error_message="Invalid username or password"
            )
            
            # リクエスト実行
            response = client.post(
                "/auth/login",
                json={
                    "username_or_email": "invaliduser",
                    "password": "wrongpassword"
                }
            )
            
            # アサーション
            assert response.status_code == 401
            data = response.json()
            assert "error" in data
            assert "Authentication failed" in data["error"]["message"]
    
    def test_login_missing_fields(self, client):
        """ログイン失敗テスト（必須フィールド不足）"""
        # ユーザー名なし
        response = client.post(
            "/auth/login",
            json={"password": "testpassword"}
        )
        assert response.status_code == 422
        
        # パスワードなし
        response = client.post(
            "/auth/login",
            json={"username_or_email": "testuser"}
        )
        assert response.status_code == 422
    
    # === ログアウトテスト ===
    
    def test_logout_success(self, client):
        """ログアウト成功テスト"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.auth.auth_service.AuthService.logout_user') as mock_logout:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_logout.return_value = True
            
            # リクエスト実行
            response = client.post(
                "/auth/logout",
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert "Successfully logged out" in data["message"]
    
    def test_logout_unauthorized(self, client):
        """ログアウト失敗テスト（未認証）"""
        response = client.post("/auth/logout")
        assert response.status_code == 401
    
    # === ユーザー登録テスト ===
    
    def test_register_success(self, client, mock_user_data):
        """ユーザー登録成功テスト"""
        with patch('src.services.user_service.UserService.register_user') as mock_register:
            
            # モック設定
            mock_register.return_value = {
                "success": True,
                "user": User(**mock_user_data)
            }
            
            # リクエスト実行
            response = client.post(
                "/auth/register",
                json={
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                    "confirm_password": "securepassword123",
                    "first_name": "New",
                    "last_name": "User"
                }
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
    
    def test_register_password_mismatch(self, client):
        """ユーザー登録失敗テスト（パスワード不一致）"""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "confirm_password": "different_password",
                "first_name": "New",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 422
    
    def test_register_duplicate_user(self, client):
        """ユーザー登録失敗テスト（重複ユーザー）"""
        with patch('src.services.user_service.UserService.register_user') as mock_register:
            
            # モック設定（重複エラー）
            mock_register.return_value = {
                "success": False,
                "error": "Username already exists"
            }
            
            # リクエスト実行
            response = client.post(
                "/auth/register",
                json={
                    "username": "existinguser",
                    "email": "existing@example.com",
                    "password": "password123",
                    "confirm_password": "password123"
                }
            )
            
            # アサーション
            assert response.status_code == 409
    
    # === トークンリフレッシュテスト ===
    
    def test_refresh_token_success(self, client):
        """トークンリフレッシュ成功テスト"""
        with patch('src.auth.auth_service.AuthService.refresh_token') as mock_refresh:
            
            # モック設定
            mock_refresh.return_value = "new_access_token"
            
            # リクエスト実行
            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "valid_refresh_token"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client):
        """トークンリフレッシュ失敗テスト（無効なトークン）"""
        with patch('src.auth.auth_service.AuthService.refresh_token') as mock_refresh:
            
            # モック設定（リフレッシュ失敗）
            mock_refresh.return_value = None
            
            # リクエスト実行
            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "invalid_refresh_token"}
            )
            
            # アサーション
            assert response.status_code == 401
    
    # === パスワード変更テスト ===
    
    def test_change_password_success(self, client):
        """パスワード変更成功テスト"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.services.user_service.UserService.change_password') as mock_change:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_change.return_value = {"success": True, "message": "Password changed successfully"}
            
            # リクエスト実行
            response = client.post(
                "/auth/change-password",
                json={
                    "current_password": "oldpassword",
                    "new_password": "newpassword123",
                    "confirm_password": "newpassword123"
                },
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert "Password changed successfully" in data["message"]
    
    def test_change_password_wrong_current(self, client):
        """パスワード変更失敗テスト（現在のパスワードが間違い）"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.services.user_service.UserService.change_password') as mock_change:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_change.return_value = {
                "success": False,
                "error": "Current password is incorrect"
            }
            
            # リクエスト実行
            response = client.post(
                "/auth/change-password",
                json={
                    "current_password": "wrongpassword",
                    "new_password": "newpassword123",
                    "confirm_password": "newpassword123"
                },
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 401
    
    # === プロフィール管理テスト ===
    
    def test_get_profile_success(self, client, mock_user_data):
        """プロフィール取得成功テスト"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.services.user_service.UserService.get_user_dashboard_data') as mock_dashboard:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_dashboard.return_value = Mock(
                user=Mock(**mock_user_data)
            )
            
            # リクエスト実行
            response = client.get(
                "/auth/profile",
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
    
    def test_update_profile_success(self, client, mock_user_data):
        """プロフィール更新成功テスト"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.services.user_service.UserService.update_user') as mock_update, \
             patch('src.services.user_service.UserService.get_user_dashboard_data') as mock_dashboard:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_update.return_value = User(**mock_user_data)
            mock_dashboard.return_value = Mock(
                user=Mock(**mock_user_data)
            )
            
            # リクエスト実行
            response = client.put(
                "/auth/profile",
                json={
                    "first_name": "Updated",
                    "last_name": "Name"
                },
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 200
    
    # === 現在のユーザー情報テスト ===
    
    def test_get_current_user_success(self, client, mock_user_data):
        """現在のユーザー情報取得成功テスト"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.services.user_service.UserService.get_user_by_id') as mock_get_user:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_get_user.return_value = User(**mock_user_data)
            
            # リクエスト実行
            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "test_user_123"
            assert data["username"] == "testuser"
    
    # === 利用可能性チェックテスト ===
    
    def test_check_username_availability_available(self, client):
        """ユーザー名利用可能性チェック（利用可能）"""
        with patch('src.services.user_service.UserService.check_username_availability') as mock_check:
            
            # モック設定
            mock_check.return_value = True
            
            # リクエスト実行
            response = client.post(
                "/auth/check-username",
                json={"username": "newuser"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is True
            assert "available" in data["message"]
    
    def test_check_username_availability_taken(self, client):
        """ユーザー名利用可能性チェック（利用不可）"""
        with patch('src.services.user_service.UserService.check_username_availability') as mock_check:
            
            # モック設定
            mock_check.return_value = False
            
            # リクエスト実行
            response = client.post(
                "/auth/check-username",
                json={"username": "existinguser"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is False
            assert "taken" in data["message"]
            assert "suggestions" in data
    
    def test_check_email_availability_available(self, client):
        """メールアドレス利用可能性チェック（利用可能）"""
        with patch('src.services.user_service.UserService.check_email_availability') as mock_check:
            
            # モック設定
            mock_check.return_value = True
            
            # リクエスト実行
            response = client.post(
                "/auth/check-email",
                json={"email": "new@example.com"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is True
    
    # === CSRFトークンテスト ===
    
    def test_get_csrf_token_success(self, client):
        """CSRFトークン取得成功テスト"""
        with patch('src.auth.dependencies.get_current_active_user') as mock_user, \
             patch('src.auth.security.SecurityManager.generate_csrf_token') as mock_csrf:
            
            # モック設定
            mock_user.return_value = Mock(user_id="test_user_123")
            mock_csrf.return_value = "mock_csrf_token"
            
            # リクエスト実行
            response = client.get(
                "/auth/csrf-token",
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # アサーション
            assert response.status_code == 200
            data = response.json()
            assert data["csrf_token"] == "mock_csrf_token"
            assert "expires_in" in data
    
    # === エラーハンドリングテスト ===
    
    def test_unauthorized_access(self, client):
        """未認証アクセステスト"""
        protected_endpoints = [
            "/auth/logout",
            "/auth/profile",
            "/auth/me",
            "/auth/change-password",
            "/auth/csrf-token"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    def test_invalid_json_format(self, client):
        """無効なJSONフォーマットテスト"""
        response = client.post(
            "/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_rate_limiting(self, client):
        """レート制限テスト"""
        with patch('src.auth.security.SecurityManager.check_rate_limit') as mock_rate_limit:
            
            # モック設定（レート制限に達した）
            mock_rate_limit.return_value = (False, "Rate limit exceeded")
            
            # リクエスト実行
            response = client.post(
                "/auth/login",
                json={
                    "username_or_email": "testuser",
                    "password": "testpassword"
                }
            )
            
            # アサーション
            assert response.status_code == 429


# === 統合テスト ===

class TestAuthIntegration:
    """認証システム統合テスト"""
    
    @pytest.fixture
    def client(self):
        """テストクライアントを作成"""
        return TestClient(app)
    
    def test_full_auth_flow(self, client):
        """完全な認証フローテスト"""
        with patch('src.services.user_service.UserService.register_user') as mock_register, \
             patch('src.auth.auth_service.AuthService.authenticate_user') as mock_auth, \
             patch('src.services.user_service.UserService.get_user_by_id') as mock_get_user:
            
            # 1. ユーザー登録
            mock_register.return_value = {
                "success": True,
                "user": Mock(user_id="test_user_123", username="testuser")
            }
            
            register_response = client.post(
                "/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "password123"
                }
            )
            assert register_response.status_code == 200
            
            # 2. ログイン
            mock_auth.return_value = Mock(
                success=True,
                user_id="test_user_123",
                access_token="mock_access_token",
                refresh_token="mock_refresh_token"
            )
            mock_get_user.return_value = Mock(
                user_id="test_user_123",
                username="testuser",
                email="test@example.com"
            )
            
            login_response = client.post(
                "/auth/login",
                json={
                    "username_or_email": "testuser",
                    "password": "password123"
                }
            )
            assert login_response.status_code == 200
            
            # 3. 認証が必要なエンドポイントにアクセス
            with patch('src.auth.dependencies.get_current_active_user') as mock_current_user:
                mock_current_user.return_value = Mock(user_id="test_user_123")
                
                me_response = client.get(
                    "/auth/me",
                    headers={"Authorization": "Bearer mock_access_token"}
                )
                assert me_response.status_code == 200