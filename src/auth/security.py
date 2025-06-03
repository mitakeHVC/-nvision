"""
セキュリティ機能

レート制限、ブルートフォース攻撃対策、セッション管理、セキュリティヘッダーの実装を提供します。
"""

import time
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """レート制限ルール"""
    max_requests: int
    window_seconds: int
    block_duration_seconds: int = 300  # 5分間ブロック


@dataclass
class SecurityEvent:
    """セキュリティイベント"""
    event_type: str
    client_ip: str
    user_id: Optional[str]
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """セキュリティマネージャー"""
    
    def __init__(self):
        """セキュリティマネージャーを初期化"""
        
        # レート制限設定
        self.rate_limits = {
            "login": RateLimitRule(max_requests=5, window_seconds=300),  # 5分間に5回
            "api": RateLimitRule(max_requests=100, window_seconds=60),   # 1分間に100回
            "search": RateLimitRule(max_requests=20, window_seconds=60), # 1分間に20回
            "password_reset": RateLimitRule(max_requests=3, window_seconds=3600)  # 1時間に3回
        }
        
        # リクエスト履歴（実際の実装ではRedisなどを使用）
        self._request_history: Dict[str, List[float]] = defaultdict(list)
        self._blocked_clients: Dict[str, float] = {}
        
        # セキュリティイベント履歴
        self._security_events: List[SecurityEvent] = []
        
        # ブルートフォース攻撃対策
        self._failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._suspicious_ips: Dict[str, datetime] = {}
        
        # セッション管理
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._session_tokens: Dict[str, str] = {}  # token -> user_id
        
        # セキュリティ設定
        self.max_failed_attempts = 5
        self.suspicious_threshold = 10
        self.session_timeout_hours = 24
        self.cleanup_interval_hours = 1
        
        # 最後のクリーンアップ時刻
        self._last_cleanup = datetime.now(timezone.utc)
    
    def check_rate_limit(
        self,
        client_ip: str,
        endpoint: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        レート制限をチェック
        
        Args:
            client_ip: クライアントIP
            endpoint: エンドポイント名
            user_id: ユーザーID（オプション）
            
        Returns:
            (許可されるか, エラーメッセージ)
        """
        try:
            # 定期クリーンアップ
            self._cleanup_old_data()
            
            # ブロック状態チェック
            if self._is_client_blocked(client_ip):
                return False, "Client is temporarily blocked"
            
            # レート制限ルール取得
            rule = self.rate_limits.get(endpoint)
            if not rule:
                return True, None
            
            # リクエスト履歴キー
            key = f"{client_ip}:{endpoint}"
            if user_id:
                key = f"{user_id}:{endpoint}"
            
            current_time = time.time()
            
            # 古いリクエストを削除
            cutoff_time = current_time - rule.window_seconds
            self._request_history[key] = [
                req_time for req_time in self._request_history[key]
                if req_time > cutoff_time
            ]
            
            # リクエスト数チェック
            if len(self._request_history[key]) >= rule.max_requests:
                # レート制限に達した
                self._block_client(client_ip, rule.block_duration_seconds)
                self._log_security_event(
                    "rate_limit_exceeded",
                    client_ip,
                    user_id,
                    {"endpoint": endpoint, "requests": len(self._request_history[key])}
                )
                return False, f"Rate limit exceeded for {endpoint}"
            
            # リクエストを記録
            self._request_history[key].append(current_time)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, None  # エラー時は許可
    
    def record_failed_login(self, client_ip: str, username: str):
        """
        ログイン失敗を記録
        
        Args:
            client_ip: クライアントIP
            username: ユーザー名
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # IP別失敗記録
            ip_key = f"ip:{client_ip}"
            self._failed_attempts[ip_key].append(current_time)
            
            # ユーザー別失敗記録
            user_key = f"user:{username}"
            self._failed_attempts[user_key].append(current_time)
            
            # 古い記録を削除（24時間以上前）
            cutoff = current_time - timedelta(hours=24)
            self._failed_attempts[ip_key] = [
                attempt for attempt in self._failed_attempts[ip_key]
                if attempt > cutoff
            ]
            self._failed_attempts[user_key] = [
                attempt for attempt in self._failed_attempts[user_key]
                if attempt > cutoff
            ]
            
            # 疑わしいIPをマーク
            if len(self._failed_attempts[ip_key]) >= self.suspicious_threshold:
                self._suspicious_ips[client_ip] = current_time
                self._log_security_event(
                    "suspicious_activity",
                    client_ip,
                    None,
                    {"failed_attempts": len(self._failed_attempts[ip_key])}
                )
            
            # ブルートフォース攻撃検出
            if len(self._failed_attempts[ip_key]) >= self.max_failed_attempts:
                self._block_client(client_ip, 3600)  # 1時間ブロック
                self._log_security_event(
                    "brute_force_attack",
                    client_ip,
                    None,
                    {"failed_attempts": len(self._failed_attempts[ip_key])}
                )
            
        except Exception as e:
            logger.error(f"Failed login recording error: {e}")
    
    def clear_failed_attempts(self, client_ip: str, username: str):
        """
        ログイン失敗記録をクリア
        
        Args:
            client_ip: クライアントIP
            username: ユーザー名
        """
        try:
            ip_key = f"ip:{client_ip}"
            user_key = f"user:{username}"
            
            if ip_key in self._failed_attempts:
                del self._failed_attempts[ip_key]
            
            if user_key in self._failed_attempts:
                del self._failed_attempts[user_key]
            
            # 疑わしいIPからも削除
            if client_ip in self._suspicious_ips:
                del self._suspicious_ips[client_ip]
                
        except Exception as e:
            logger.error(f"Failed attempts clearing error: {e}")
    
    def create_secure_session(
        self,
        user_id: str,
        client_ip: str,
        user_agent: str
    ) -> str:
        """
        セキュアなセッションを作成
        
        Args:
            user_id: ユーザーID
            client_ip: クライアントIP
            user_agent: ユーザーエージェント
            
        Returns:
            セッショントークン
        """
        try:
            # セッショントークン生成
            session_token = secrets.token_urlsafe(32)
            
            # セッション情報
            session_data = {
                "user_id": user_id,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "is_active": True
            }
            
            # セッション保存
            self._active_sessions[session_token] = session_data
            self._session_tokens[session_token] = user_id
            
            self._log_security_event(
                "session_created",
                client_ip,
                user_id,
                {"session_token": session_token[:8] + "..."}
            )
            
            return session_token
            
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            raise
    
    def validate_session(
        self,
        session_token: str,
        client_ip: str,
        user_agent: str
    ) -> Optional[str]:
        """
        セッションを検証
        
        Args:
            session_token: セッショントークン
            client_ip: クライアントIP
            user_agent: ユーザーエージェント
            
        Returns:
            ユーザーID、または None（無効な場合）
        """
        try:
            if session_token not in self._active_sessions:
                return None
            
            session_data = self._active_sessions[session_token]
            
            # セッション有効性チェック
            if not session_data.get("is_active", False):
                return None
            
            # タイムアウトチェック
            last_activity = session_data["last_activity"]
            timeout = last_activity + timedelta(hours=self.session_timeout_hours)
            
            if datetime.now(timezone.utc) > timeout:
                self._invalidate_session(session_token)
                return None
            
            # IP・ユーザーエージェントチェック（セッションハイジャック対策）
            if session_data["client_ip"] != client_ip:
                self._log_security_event(
                    "session_hijack_attempt",
                    client_ip,
                    session_data["user_id"],
                    {
                        "original_ip": session_data["client_ip"],
                        "new_ip": client_ip
                    }
                )
                self._invalidate_session(session_token)
                return None
            
            # 最終活動時刻を更新
            session_data["last_activity"] = datetime.now(timezone.utc)
            
            return session_data["user_id"]
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def invalidate_session(self, session_token: str):
        """
        セッションを無効化
        
        Args:
            session_token: セッショントークン
        """
        self._invalidate_session(session_token)
    
    def _invalidate_session(self, session_token: str):
        """セッション無効化の内部実装"""
        try:
            if session_token in self._active_sessions:
                session_data = self._active_sessions[session_token]
                session_data["is_active"] = False
                
                self._log_security_event(
                    "session_invalidated",
                    session_data.get("client_ip", "unknown"),
                    session_data.get("user_id"),
                    {"session_token": session_token[:8] + "..."}
                )
                
                del self._active_sessions[session_token]
            
            if session_token in self._session_tokens:
                del self._session_tokens[session_token]
                
        except Exception as e:
            logger.error(f"Session invalidation error: {e}")
    
    def get_security_headers(self) -> Dict[str, str]:
        """
        セキュリティヘッダーを取得
        
        Returns:
            セキュリティヘッダーの辞書
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        }
    
    def generate_csrf_token(self, session_token: str) -> str:
        """
        CSRFトークンを生成
        
        Args:
            session_token: セッショントークン
            
        Returns:
            CSRFトークン
        """
        # セッショントークンとタイムスタンプからCSRFトークンを生成
        timestamp = str(int(time.time()))
        data = f"{session_token}:{timestamp}"
        csrf_token = hashlib.sha256(data.encode()).hexdigest()
        
        return f"{csrf_token}:{timestamp}"
    
    def validate_csrf_token(
        self,
        csrf_token: str,
        session_token: str,
        max_age_seconds: int = 3600
    ) -> bool:
        """
        CSRFトークンを検証
        
        Args:
            csrf_token: CSRFトークン
            session_token: セッショントークン
            max_age_seconds: 最大有効期間（秒）
            
        Returns:
            有効な場合 True
        """
        try:
            if ":" not in csrf_token:
                return False
            
            token_hash, timestamp_str = csrf_token.rsplit(":", 1)
            timestamp = int(timestamp_str)
            
            # 有効期限チェック
            current_time = int(time.time())
            if current_time - timestamp > max_age_seconds:
                return False
            
            # トークン検証
            expected_data = f"{session_token}:{timestamp_str}"
            expected_hash = hashlib.sha256(expected_data.encode()).hexdigest()
            
            return token_hash == expected_hash
            
        except (ValueError, TypeError):
            return False
    
    def _is_client_blocked(self, client_ip: str) -> bool:
        """クライアントがブロックされているかチェック"""
        if client_ip not in self._blocked_clients:
            return False
        
        block_until = self._blocked_clients[client_ip]
        current_time = time.time()
        
        if current_time > block_until:
            # ブロック期間終了
            del self._blocked_clients[client_ip]
            return False
        
        return True
    
    def _block_client(self, client_ip: str, duration_seconds: int):
        """クライアントをブロック"""
        block_until = time.time() + duration_seconds
        self._blocked_clients[client_ip] = block_until
        
        logger.warning(f"Client {client_ip} blocked for {duration_seconds} seconds")
    
    def _log_security_event(
        self,
        event_type: str,
        client_ip: str,
        user_id: Optional[str],
        details: Dict[str, Any]
    ):
        """セキュリティイベントをログ"""
        event = SecurityEvent(
            event_type=event_type,
            client_ip=client_ip,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            details=details
        )
        
        self._security_events.append(event)
        
        # ログ出力
        logger.warning(
            f"Security event: {event_type} from {client_ip} "
            f"(user: {user_id or 'unknown'}) - {details}"
        )
        
        # イベント履歴の制限（最新1000件のみ保持）
        if len(self._security_events) > 1000:
            self._security_events = self._security_events[-1000:]
    
    def _cleanup_old_data(self):
        """古いデータをクリーンアップ"""
        current_time = datetime.now(timezone.utc)
        
        # 1時間ごとにクリーンアップ
        if current_time - self._last_cleanup < timedelta(hours=self.cleanup_interval_hours):
            return
        
        try:
            # 古いリクエスト履歴を削除
            cutoff_time = time.time() - 3600  # 1時間前
            for key in list(self._request_history.keys()):
                self._request_history[key] = [
                    req_time for req_time in self._request_history[key]
                    if req_time > cutoff_time
                ]
                if not self._request_history[key]:
                    del self._request_history[key]
            
            # 期限切れブロックを削除
            current_timestamp = time.time()
            expired_blocks = [
                ip for ip, block_until in self._blocked_clients.items()
                if current_timestamp > block_until
            ]
            for ip in expired_blocks:
                del self._blocked_clients[ip]
            
            # 古い失敗記録を削除
            cutoff_datetime = current_time - timedelta(hours=24)
            for key in list(self._failed_attempts.keys()):
                self._failed_attempts[key] = [
                    attempt for attempt in self._failed_attempts[key]
                    if attempt > cutoff_datetime
                ]
                if not self._failed_attempts[key]:
                    del self._failed_attempts[key]
            
            # 古い疑わしいIP記録を削除
            expired_suspicious = [
                ip for ip, timestamp in self._suspicious_ips.items()
                if current_time - timestamp > timedelta(hours=24)
            ]
            for ip in expired_suspicious:
                del self._suspicious_ips[ip]
            
            self._last_cleanup = current_time
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """
        セキュリティ統計を取得
        
        Returns:
            セキュリティ統計情報
        """
        current_time = datetime.now(timezone.utc)
        
        # 最近24時間のイベント
        recent_events = [
            event for event in self._security_events
            if current_time - event.timestamp < timedelta(hours=24)
        ]
        
        # イベントタイプ別集計
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event.event_type] += 1
        
        return {
            "active_sessions": len(self._active_sessions),
            "blocked_clients": len(self._blocked_clients),
            "suspicious_ips": len(self._suspicious_ips),
            "recent_events_24h": len(recent_events),
            "event_types": dict(event_counts),
            "failed_attempts": len(self._failed_attempts),
            "last_cleanup": self._last_cleanup.isoformat()
        }