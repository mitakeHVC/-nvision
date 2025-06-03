"""
認証データベース初期化

管理者ユーザー、デフォルトロール、権限の初期化を行います。
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from ..auth.password_handler import PasswordHandler
from ..auth.permissions import PermissionManager, Role, Permission
from ..repositories.user_repository import UserRepository
from ..models.user_models import UserCreate
from ..services.user_service import UserService
from ..auth.auth_service import AuthService
from ..auth.jwt_handler import JWTHandler
from ..config.auth_config import get_auth_settings

logger = logging.getLogger(__name__)


class AuthDataInitializer:
    """認証データ初期化クラス"""
    
    def __init__(self):
        """初期化"""
        self.auth_settings = get_auth_settings()
        self.password_handler = PasswordHandler()
        self.permission_manager = PermissionManager()
        self.jwt_handler = JWTHandler(
            secret_key=self.auth_settings.jwt_secret_key,
            algorithm=self.auth_settings.jwt_algorithm
        )
        
        # リポジトリとサービス
        self.user_repository = UserRepository(connection_manager=None)
        self.auth_service = AuthService(
            jwt_handler=self.jwt_handler,
            password_handler=self.password_handler,
            permission_manager=self.permission_manager
        )
        self.user_service = UserService(
            user_repository=self.user_repository,
            auth_service=self.auth_service,
            permission_manager=self.permission_manager
        )
    
    async def initialize_all(self):
        """全ての初期化を実行"""
        try:
            logger.info("Starting authentication data initialization...")
            
            # 1. ロールと権限の初期化
            await self.initialize_roles_and_permissions()
            
            # 2. 管理者ユーザーの作成
            await self.create_admin_users()
            
            # 3. デフォルトユーザーの作成（開発環境のみ）
            if self.auth_settings.debug_mode:
                await self.create_default_users()
            
            logger.info("Authentication data initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Authentication data initialization failed: {e}")
            raise
    
    async def initialize_roles_and_permissions(self):
        """ロールと権限を初期化"""
        logger.info("Initializing roles and permissions...")
        
        # 権限マネージャーは既にデフォルトロールを設定済み
        # 追加のカスタムロールがあればここで設定
        
        # カスタムロールの例
        custom_roles = {
            "data_scientist": {
                "description": "データサイエンティスト",
                "permissions": [
                    Permission.API_ACCESS,
                    Permission.CUSTOMER_READ,
                    Permission.CUSTOMER_LIST,
                    Permission.PRODUCT_READ,
                    Permission.PRODUCT_LIST,
                    Permission.ORDER_READ,
                    Permission.ORDER_LIST,
                    Permission.SEARCH_VECTOR,
                    Permission.SEARCH_SEMANTIC,
                    Permission.SEARCH_ADVANCED,
                    Permission.ANALYTICS_READ,
                    Permission.ANALYTICS_EXPORT,
                    Permission.ANALYTICS_ADVANCED,
                    Permission.RECOMMENDATION_READ
                ]
            },
            "customer_support": {
                "description": "カスタマーサポート",
                "permissions": [
                    Permission.API_ACCESS,
                    Permission.CUSTOMER_READ,
                    Permission.CUSTOMER_UPDATE,
                    Permission.CUSTOMER_LIST,
                    Permission.ORDER_READ,
                    Permission.ORDER_UPDATE,
                    Permission.ORDER_LIST,
                    Permission.SEARCH_VECTOR,
                    Permission.SEARCH_SEMANTIC
                ]
            }
        }
        
        for role_name, role_config in custom_roles.items():
            self.permission_manager.define_role(
                role_name=role_name,
                description=role_config["description"],
                permissions=set(role_config["permissions"])
            )
        
        logger.info(f"Initialized {len(custom_roles)} custom roles")
    
    async def create_admin_users(self):
        """管理者ユーザーを作成"""
        logger.info("Creating admin users...")
        
        admin_users = [
            {
                "username": "admin",
                "email": "admin@nvision.com",
                "password": "admin123!@#",  # 本番環境では強力なパスワードを使用
                "first_name": "System",
                "last_name": "Administrator",
                "roles": [Role.SUPER_ADMIN.value]
            },
            {
                "username": "manager",
                "email": "manager@nvision.com",
                "password": "manager123!@#",
                "first_name": "System",
                "last_name": "Manager",
                "roles": [Role.MANAGER.value]
            }
        ]
        
        for admin_data in admin_users:
            await self._create_user_if_not_exists(admin_data)
        
        logger.info(f"Created {len(admin_users)} admin users")
    
    async def create_default_users(self):
        """デフォルトユーザーを作成（開発環境のみ）"""
        logger.info("Creating default users for development...")
        
        default_users = [
            {
                "username": "analyst",
                "email": "analyst@nvision.com",
                "password": "analyst123",
                "first_name": "Data",
                "last_name": "Analyst",
                "roles": [Role.ANALYST.value]
            },
            {
                "username": "operator",
                "email": "operator@nvision.com",
                "password": "operator123",
                "first_name": "System",
                "last_name": "Operator",
                "roles": [Role.OPERATOR.value]
            },
            {
                "username": "viewer",
                "email": "viewer@nvision.com",
                "password": "viewer123",
                "first_name": "Read",
                "last_name": "Only",
                "roles": [Role.VIEWER.value]
            },
            {
                "username": "support",
                "email": "support@nvision.com",
                "password": "support123",
                "first_name": "Customer",
                "last_name": "Support",
                "roles": ["customer_support"]
            },
            {
                "username": "scientist",
                "email": "scientist@nvision.com",
                "password": "scientist123",
                "first_name": "Data",
                "last_name": "Scientist",
                "roles": ["data_scientist"]
            }
        ]
        
        for user_data in default_users:
            await self._create_user_if_not_exists(user_data)
        
        logger.info(f"Created {len(default_users)} default users")
    
    async def _create_user_if_not_exists(self, user_data: Dict[str, Any]):
        """ユーザーが存在しない場合のみ作成"""
        try:
            # ユーザー存在チェック
            existing_user = await self.user_repository.get_user_by_username(user_data["username"])
            if existing_user:
                logger.info(f"User '{user_data['username']}' already exists, skipping...")
                return
            
            # メールアドレス存在チェック
            existing_email = await self.user_repository.get_user_by_email(user_data["email"])
            if existing_email:
                logger.info(f"Email '{user_data['email']}' already exists, skipping...")
                return
            
            # ユーザー作成データを準備
            user_create = UserCreate(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                confirm_password=user_data["password"],
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                roles=user_data.get("roles", [Role.VIEWER.value])
            )
            
            # ユーザー登録
            result = await self.user_service.register_user(user_create)
            
            if result["success"]:
                user_id = result["user_id"]
                
                # ロール割り当て
                for role_name in user_data.get("roles", []):
                    self.permission_manager.assign_role_to_user(user_id, role_name)
                
                logger.info(f"Created user '{user_data['username']}' with roles {user_data.get('roles', [])}")
            else:
                logger.error(f"Failed to create user '{user_data['username']}': {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error creating user '{user_data['username']}': {e}")
    
    async def verify_initialization(self):
        """初期化の検証"""
        logger.info("Verifying authentication data initialization...")
        
        try:
            # 管理者ユーザーの存在確認
            admin_user = await self.user_repository.get_user_by_username("admin")
            if not admin_user:
                raise ValueError("Admin user not found")
            
            # 管理者権限の確認
            admin_roles = self.permission_manager.get_user_roles(admin_user.user_id)
            if Role.SUPER_ADMIN.value not in admin_roles:
                raise ValueError("Admin user does not have super admin role")
            
            # 権限の確認
            admin_permissions = self.permission_manager.get_user_permissions(admin_user.user_id)
            if not admin_permissions:
                raise ValueError("Admin user has no permissions")
            
            logger.info("Authentication data verification completed successfully")
            
            # 統計情報をログ出力
            await self._log_initialization_stats()
            
        except Exception as e:
            logger.error(f"Authentication data verification failed: {e}")
            raise
    
    async def _log_initialization_stats(self):
        """初期化統計をログ出力"""
        try:
            # ユーザー統計
            all_users = list(self.user_repository._users.values())
            total_users = len(all_users)
            active_users = len([u for u in all_users if u.is_active])
            
            # ロール統計
            all_roles = self.permission_manager.get_all_roles()
            
            # 権限統計
            total_permissions = len(Permission)
            
            logger.info("=== Authentication Data Initialization Stats ===")
            logger.info(f"Total Users: {total_users}")
            logger.info(f"Active Users: {active_users}")
            logger.info(f"Total Roles: {len(all_roles)}")
            logger.info(f"Total Permissions: {total_permissions}")
            
            # ロール別ユーザー数
            role_counts = {}
            for user in all_users:
                for role in user.roles:
                    role_counts[role] = role_counts.get(role, 0) + 1
            
            logger.info("Users by Role:")
            for role, count in role_counts.items():
                logger.info(f"  {role}: {count}")
            
            logger.info("=== End Stats ===")
            
        except Exception as e:
            logger.error(f"Failed to log initialization stats: {e}")


# === 初期化実行関数 ===

async def initialize_auth_data():
    """認証データを初期化"""
    initializer = AuthDataInitializer()
    
    try:
        await initializer.initialize_all()
        await initializer.verify_initialization()
        return True
    except Exception as e:
        logger.error(f"Authentication data initialization failed: {e}")
        return False


async def reset_auth_data():
    """認証データをリセット（開発環境のみ）"""
    auth_settings = get_auth_settings()
    
    if not auth_settings.debug_mode:
        raise ValueError("Reset is only allowed in debug mode")
    
    logger.warning("Resetting authentication data...")
    
    initializer = AuthDataInitializer()
    
    # データクリア
    initializer.user_repository._users.clear()
    initializer.user_repository._users_by_username.clear()
    initializer.user_repository._users_by_email.clear()
    initializer.permission_manager.clear_user_permissions("all")
    
    # 再初期化
    await initializer.initialize_all()
    await initializer.verify_initialization()
    
    logger.info("Authentication data reset completed")


# === CLI実行用 ===

if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) > 1 and sys.argv[1] == "reset":
            success = await reset_auth_data()
        else:
            success = await initialize_auth_data()
        
        if success:
            print("Authentication data initialization completed successfully")
            sys.exit(0)
        else:
            print("Authentication data initialization failed")
            sys.exit(1)
    
    asyncio.run(main())