"""
セキュリティマネージャー（ダミー実装）

実際の運用フローテスト用のダミーセキュリティマネージャーです。
"""


class SecurityManager:
    """セキュリティマネージャー（ダミー実装）"""
    
    def record_failed_login(self, ip: str, username: str):
        """ログイン失敗を記録"""
        pass
    
    def clear_failed_attempts(self, ip: str, username: str):
        """ログイン失敗回数をクリア"""
        pass
    
    def create_secure_session(self, user_id: int, client_ip: str, user_agent: str):
        """セキュアセッションを作成"""
        return "dummy_session_token"
    
    def generate_csrf_token(self, session_token: str):
        """CSRFトークンを生成"""
        return "dummy_csrf_token"