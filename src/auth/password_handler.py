"""
パスワードハッシュ化・検証ハンドラー

bcryptを使用したセキュアなパスワードハッシュ化と検証機能を提供します。
"""

import bcrypt
import secrets
import string
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PasswordHandler:
    """パスワードハッシュ化・検証ハンドラー"""
    
    def __init__(self, rounds: int = 12):
        """
        パスワードハンドラーを初期化
        
        Args:
            rounds: bcryptのラウンド数（デフォルト: 12）
        """
        self.rounds = rounds
    
    def hash_password(self, password: str) -> str:
        """
        パスワードをハッシュ化
        
        Args:
            password: プレーンテキストパスワード
            
        Returns:
            ハッシュ化されたパスワード
            
        Raises:
            ValueError: パスワードが空の場合
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        try:
            # パスワードをバイト列に変換
            password_bytes = password.encode('utf-8')
            
            # ソルトを生成してハッシュ化
            salt = bcrypt.gensalt(rounds=self.rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            # 文字列として返す
            hashed_str = hashed.decode('utf-8')
            
            logger.info("Password hashed successfully")
            return hashed_str
            
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        パスワードを検証
        
        Args:
            password: プレーンテキストパスワード
            hashed_password: ハッシュ化されたパスワード
            
        Returns:
            パスワードが一致する場合 True
        """
        if not password or not hashed_password:
            return False
        
        try:
            # パスワードをバイト列に変換
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            # パスワードを検証
            result = bcrypt.checkpw(password_bytes, hashed_bytes)
            
            if result:
                logger.info("Password verification successful")
            else:
                logger.warning("Password verification failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def generate_random_password(
        self,
        length: int = 12,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_symbols: bool = True,
        exclude_ambiguous: bool = True
    ) -> str:
        """
        ランダムパスワードを生成
        
        Args:
            length: パスワードの長さ
            include_uppercase: 大文字を含める
            include_lowercase: 小文字を含める
            include_digits: 数字を含める
            include_symbols: 記号を含める
            exclude_ambiguous: 紛らわしい文字を除外（0, O, l, I など）
            
        Returns:
            生成されたランダムパスワード
            
        Raises:
            ValueError: 無効なパラメータの場合
        """
        if length < 4:
            raise ValueError("Password length must be at least 4")
        
        if not any([include_uppercase, include_lowercase, include_digits, include_symbols]):
            raise ValueError("At least one character type must be included")
        
        # 文字セットを構築
        charset = ""
        
        if include_lowercase:
            chars = string.ascii_lowercase
            if exclude_ambiguous:
                chars = chars.replace('l', '').replace('o', '')
            charset += chars
        
        if include_uppercase:
            chars = string.ascii_uppercase
            if exclude_ambiguous:
                chars = chars.replace('I', '').replace('O', '')
            charset += chars
        
        if include_digits:
            chars = string.digits
            if exclude_ambiguous:
                chars = chars.replace('0', '').replace('1', '')
            charset += chars
        
        if include_symbols:
            chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            charset += chars
        
        if not charset:
            raise ValueError("No valid characters available for password generation")
        
        try:
            # セキュアなランダム生成
            password = ''.join(secrets.choice(charset) for _ in range(length))
            
            # 各文字タイプが少なくとも1つ含まれることを保証
            required_chars = []
            
            if include_lowercase:
                chars = string.ascii_lowercase
                if exclude_ambiguous:
                    chars = chars.replace('l', '').replace('o', '')
                if chars:
                    required_chars.append(secrets.choice(chars))
            
            if include_uppercase:
                chars = string.ascii_uppercase
                if exclude_ambiguous:
                    chars = chars.replace('I', '').replace('O', '')
                if chars:
                    required_chars.append(secrets.choice(chars))
            
            if include_digits:
                chars = string.digits
                if exclude_ambiguous:
                    chars = chars.replace('0', '').replace('1', '')
                if chars:
                    required_chars.append(secrets.choice(chars))
            
            if include_symbols:
                chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
                required_chars.append(secrets.choice(chars))
            
            # 必要な文字をランダムな位置に挿入
            password_list = list(password)
            for i, char in enumerate(required_chars):
                if i < len(password_list):
                    pos = secrets.randbelow(len(password_list))
                    password_list[pos] = char
            
            result = ''.join(password_list)
            
            logger.info(f"Random password generated with length {length}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate random password: {e}")
            raise
    
    def check_password_strength(self, password: str) -> dict:
        """
        パスワード強度をチェック
        
        Args:
            password: チェックするパスワード
            
        Returns:
            パスワード強度の詳細情報
        """
        if not password:
            return {
                "score": 0,
                "strength": "very_weak",
                "issues": ["Password is empty"],
                "suggestions": ["Please provide a password"]
            }
        
        score = 0
        issues = []
        suggestions = []
        
        # 長さチェック
        length = len(password)
        if length < 8:
            issues.append("Password is too short")
            suggestions.append("Use at least 8 characters")
        elif length >= 8:
            score += 1
        
        if length >= 12:
            score += 1
        
        # 文字タイプチェック
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        char_types = sum([has_lower, has_upper, has_digit, has_symbol])
        
        if char_types < 2:
            issues.append("Password lacks character variety")
            suggestions.append("Include uppercase, lowercase, numbers, and symbols")
        elif char_types >= 3:
            score += 1
        
        if char_types >= 4:
            score += 1
        
        # 繰り返しパターンチェック
        if len(set(password)) < len(password) * 0.6:
            issues.append("Too many repeated characters")
            suggestions.append("Avoid repeating characters")
        else:
            score += 1
        
        # 一般的なパスワードチェック
        common_passwords = [
            "password", "123456", "123456789", "qwerty", "abc123",
            "password123", "admin", "letmein", "welcome", "monkey"
        ]
        
        if password.lower() in common_passwords:
            issues.append("Password is too common")
            suggestions.append("Avoid common passwords")
        else:
            score += 1
        
        # 強度判定
        if score <= 1:
            strength = "very_weak"
        elif score <= 2:
            strength = "weak"
        elif score <= 3:
            strength = "medium"
        elif score <= 4:
            strength = "strong"
        else:
            strength = "very_strong"
        
        return {
            "score": score,
            "strength": strength,
            "length": length,
            "has_lowercase": has_lower,
            "has_uppercase": has_upper,
            "has_digits": has_digit,
            "has_symbols": has_symbol,
            "character_types": char_types,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def is_password_secure(self, password: str, min_score: int = 3) -> bool:
        """
        パスワードが十分にセキュアかチェック
        
        Args:
            password: チェックするパスワード
            min_score: 最小スコア（デフォルト: 3）
            
        Returns:
            セキュアな場合 True
        """
        strength_info = self.check_password_strength(password)
        return strength_info["score"] >= min_score