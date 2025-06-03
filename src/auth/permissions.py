"""
権限管理システム

ロールベースアクセス制御（RBAC）の実装を提供します。
"""

from enum import Enum
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class Permission(Enum):
    """システム権限の定義"""
    
    # ユーザー管理権限
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # 顧客管理権限
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_READ = "customer:read"
    CUSTOMER_UPDATE = "customer:update"
    CUSTOMER_DELETE = "customer:delete"
    CUSTOMER_LIST = "customer:list"
    
    # 商品管理権限
    PRODUCT_CREATE = "product:create"
    PRODUCT_READ = "product:read"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"
    PRODUCT_LIST = "product:list"
    
    # 注文管理権限
    ORDER_CREATE = "order:create"
    ORDER_READ = "order:read"
    ORDER_UPDATE = "order:update"
    ORDER_DELETE = "order:delete"
    ORDER_LIST = "order:list"
    
    # 検索権限
    SEARCH_VECTOR = "search:vector"
    SEARCH_SEMANTIC = "search:semantic"
    SEARCH_ADVANCED = "search:advanced"
    
    # 分析権限
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_ADVANCED = "analytics:advanced"
    
    # レコメンデーション権限
    RECOMMENDATION_READ = "recommendation:read"
    RECOMMENDATION_MANAGE = "recommendation:manage"
    
    # システム管理権限
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    
    # API管理権限
    API_ACCESS = "api:access"
    API_ADMIN = "api:admin"

    # Client Preferences Management
    CLIENT_PREFERENCES_CREATE = "client_preferences:create"
    CLIENT_PREFERENCES_READ = "client_preferences:read"
    CLIENT_PREFERENCES_UPDATE = "client_preferences:update"
    CLIENT_PREFERENCES_DELETE = "client_preferences:delete"

    # Suggestion Engine Permissions
    SUGGESTION_READ = "suggestion:read"
    ACTION_PLAN_UPDATE = "action_plan:update" # Covers updating step status


class Role(Enum):
    """システムロールの定義"""
    
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


@dataclass
class RoleDefinition:
    """ロール定義"""
    name: str
    description: str
    permissions: Set[Permission]
    inherits_from: Optional[List[str]] = None


class PermissionManager:
    """権限管理マネージャー"""
    
    def __init__(self):
        """権限マネージャーを初期化"""
        self._role_definitions: Dict[str, RoleDefinition] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._user_permissions: Dict[str, Set[Permission]] = {}
        
        # デフォルトロールを設定
        self._setup_default_roles()
    
    def _setup_default_roles(self):
        """デフォルトロールを設定"""
        
        # ゲストロール（最小権限）
        self.define_role(
            Role.GUEST.value,
            "ゲストユーザー",
            {Permission.API_ACCESS}
        )
        
        # ビューアーロール（読み取り専用）
        self.define_role(
            Role.VIEWER.value,
            "閲覧者",
            {
                Permission.API_ACCESS,
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_LIST,
                Permission.PRODUCT_READ,
                Permission.PRODUCT_LIST,
                Permission.ORDER_READ,
                Permission.ORDER_LIST,
                Permission.SEARCH_VECTOR,
                Permission.RECOMMENDATION_READ
            }
        )
        
        # オペレーターロール（基本操作）
        self.define_role(
            Role.OPERATOR.value,
            "オペレーター",
            {
                Permission.API_ACCESS,
                Permission.CUSTOMER_CREATE,
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_LIST,
                Permission.PRODUCT_READ,
                Permission.PRODUCT_LIST,
                Permission.ORDER_CREATE,
                Permission.ORDER_READ,
                Permission.ORDER_UPDATE,
                Permission.ORDER_LIST,
                Permission.SEARCH_VECTOR,
                Permission.SEARCH_SEMANTIC,
                Permission.RECOMMENDATION_READ
            }
        )
        
        # アナリストロール（分析機能）
        self.define_role(
            Role.ANALYST.value,
            "アナリスト",
            {
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
            }
        )
        
        # マネージャーロール（管理機能）
        self.define_role(
            Role.MANAGER.value,
            "マネージャー",
            {
                Permission.API_ACCESS,
                Permission.USER_READ,
                Permission.USER_LIST,
                Permission.CUSTOMER_CREATE,
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_DELETE,
                Permission.CUSTOMER_LIST,
                Permission.PRODUCT_CREATE,
                Permission.PRODUCT_READ,
                Permission.PRODUCT_UPDATE,
                Permission.PRODUCT_DELETE,
                Permission.PRODUCT_LIST,
                Permission.ORDER_CREATE,
                Permission.ORDER_READ,
                Permission.ORDER_UPDATE,
                Permission.ORDER_DELETE,
                Permission.ORDER_LIST,
                Permission.SEARCH_VECTOR,
                Permission.SEARCH_SEMANTIC,
                Permission.SEARCH_ADVANCED,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.ANALYTICS_ADVANCED,
                Permission.RECOMMENDATION_READ,
                Permission.RECOMMENDATION_MANAGE
            }
        )
        
        # 管理者ロール（システム管理）
        self.define_role(
            Role.ADMIN.value,
            "管理者",
            {
                Permission.API_ACCESS,
                Permission.API_ADMIN,
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_DELETE,
                Permission.USER_LIST,
                Permission.CUSTOMER_CREATE,
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_DELETE,
                Permission.CUSTOMER_LIST,
                Permission.PRODUCT_CREATE,
                Permission.PRODUCT_READ,
                Permission.PRODUCT_UPDATE,
                Permission.PRODUCT_DELETE,
                Permission.PRODUCT_LIST,
                Permission.ORDER_CREATE,
                Permission.ORDER_READ,
                Permission.ORDER_UPDATE,
                Permission.ORDER_DELETE,
                Permission.ORDER_LIST,
                Permission.SEARCH_VECTOR,
                Permission.SEARCH_SEMANTIC,
                Permission.SEARCH_ADVANCED,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.ANALYTICS_ADVANCED,
                Permission.RECOMMENDATION_READ,
                Permission.RECOMMENDATION_MANAGE,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_LOGS
            }
        )
        
        # スーパー管理者ロール（全権限）
        self.define_role(
            Role.SUPER_ADMIN.value,
            "スーパー管理者",
            set(Permission)  # 全権限
        )

        # Add new permissions to relevant roles, e.g., ADMIN and MANAGER
        # For example, giving MANAGER all client preference permissions
        if Role.MANAGER.value in self._role_definitions:
            self._role_definitions[Role.MANAGER.value].permissions.update({
                Permission.CLIENT_PREFERENCES_CREATE,
                Permission.CLIENT_PREFERENCES_READ,
                Permission.CLIENT_PREFERENCES_UPDATE,
                Permission.CLIENT_PREFERENCES_DELETE,
                Permission.SUGGESTION_READ,         # Manager can read suggestions
                Permission.ACTION_PLAN_UPDATE,      # Manager can update action plans
            })
            logger.info(f"Client preference, suggestion, and action plan permissions added to role '{Role.MANAGER.value}'")

        # Ensure ANALYST can read preferences and suggestions
        if Role.ANALYST.value in self._role_definitions:
             self._role_definitions[Role.ANALYST.value].permissions.update({
                Permission.CLIENT_PREFERENCES_READ,
                Permission.SUGGESTION_READ,         # Analyst can read suggestions
                # ACTION_PLAN_UPDATE could be analyst or manager only, let's give to manager for now
             })
             logger.info(f"Client preference and suggestion read permissions added to role '{Role.ANALYST.value}'")
    
    def define_role(
        self,
        role_name: str,
        description: str,
        permissions: Set[Permission],
        inherits_from: Optional[List[str]] = None
    ):
        """
        ロールを定義
        
        Args:
            role_name: ロール名
            description: ロールの説明
            permissions: ロールの権限セット
            inherits_from: 継承元ロール
        """
        # 継承権限を追加
        if inherits_from:
            for parent_role in inherits_from:
                if parent_role in self._role_definitions:
                    permissions.update(self._role_definitions[parent_role].permissions)
        
        self._role_definitions[role_name] = RoleDefinition(
            name=role_name,
            description=description,
            permissions=permissions,
            inherits_from=inherits_from
        )
        
        logger.info(f"Role '{role_name}' defined with {len(permissions)} permissions")
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """
        ユーザーにロールを割り当て
        
        Args:
            user_id: ユーザーID
            role_name: ロール名
            
        Returns:
            成功した場合 True
        """
        if role_name not in self._role_definitions:
            logger.error(f"Role '{role_name}' not found")
            return False
        
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        
        self._user_roles[user_id].add(role_name)
        
        # ユーザー権限を更新
        self._update_user_permissions(user_id)
        
        logger.info(f"Role '{role_name}' assigned to user {user_id}")
        return True
    
    def remove_role_from_user(self, user_id: str, role_name: str) -> bool:
        """
        ユーザーからロールを削除
        
        Args:
            user_id: ユーザーID
            role_name: ロール名
            
        Returns:
            成功した場合 True
        """
        if user_id not in self._user_roles:
            return False
        
        if role_name in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role_name)
            
            # ユーザー権限を更新
            self._update_user_permissions(user_id)
            
            logger.info(f"Role '{role_name}' removed from user {user_id}")
            return True
        
        return False
    
    def grant_permission_to_user(self, user_id: str, permission: Permission) -> bool:
        """
        ユーザーに直接権限を付与
        
        Args:
            user_id: ユーザーID
            permission: 権限
            
        Returns:
            成功した場合 True
        """
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = set()
        
        self._user_permissions[user_id].add(permission)
        
        logger.info(f"Permission '{permission.value}' granted to user {user_id}")
        return True
    
    def revoke_permission_from_user(self, user_id: str, permission: Permission) -> bool:
        """
        ユーザーから直接権限を削除
        
        Args:
            user_id: ユーザーID
            permission: 権限
            
        Returns:
            成功した場合 True
        """
        if user_id not in self._user_permissions:
            return False
        
        if permission in self._user_permissions[user_id]:
            self._user_permissions[user_id].remove(permission)
            
            logger.info(f"Permission '{permission.value}' revoked from user {user_id}")
            return True
        
        return False
    
    def _update_user_permissions(self, user_id: str):
        """ユーザーの権限を更新"""
        if user_id not in self._user_roles:
            return
        
        permissions = set()
        
        # ロールから権限を収集
        for role_name in self._user_roles[user_id]:
            if role_name in self._role_definitions:
                permissions.update(self._role_definitions[role_name].permissions)
        
        # 直接付与された権限を追加
        if user_id in self._user_permissions:
            permissions.update(self._user_permissions[user_id])
        
        self._user_permissions[user_id] = permissions
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """
        ユーザーが特定の権限を持っているかチェック
        
        Args:
            user_id: ユーザーID
            permission: チェックする権限
            
        Returns:
            権限を持っている場合 True
        """
        if user_id not in self._user_permissions:
            return False
        
        return permission in self._user_permissions[user_id]
    
    def has_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """
        ユーザーが指定された権限のいずれかを持っているかチェック
        
        Args:
            user_id: ユーザーID
            permissions: チェックする権限リスト
            
        Returns:
            いずれかの権限を持っている場合 True
        """
        if user_id not in self._user_permissions:
            return False
        
        user_perms = self._user_permissions[user_id]
        return any(perm in user_perms for perm in permissions)
    
    def has_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """
        ユーザーが指定された全ての権限を持っているかチェック
        
        Args:
            user_id: ユーザーID
            permissions: チェックする権限リスト
            
        Returns:
            全ての権限を持っている場合 True
        """
        if user_id not in self._user_permissions:
            return False
        
        user_perms = self._user_permissions[user_id]
        return all(perm in user_perms for perm in permissions)
    
    def has_role(self, user_id: str, role_name: str) -> bool:
        """
        ユーザーが特定のロールを持っているかチェック
        
        Args:
            user_id: ユーザーID
            role_name: ロール名
            
        Returns:
            ロールを持っている場合 True
        """
        if user_id not in self._user_roles:
            return False
        
        return role_name in self._user_roles[user_id]
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """
        ユーザーのロール一覧を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ロール名のリスト
        """
        if user_id not in self._user_roles:
            return []
        
        return list(self._user_roles[user_id])
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """
        ユーザーの権限一覧を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            権限名のリスト
        """
        if user_id not in self._user_permissions:
            return []
        
        return [perm.value for perm in self._user_permissions[user_id]]
    
    def get_role_permissions(self, role_name: str) -> List[str]:
        """
        ロールの権限一覧を取得
        
        Args:
            role_name: ロール名
            
        Returns:
            権限名のリスト
        """
        if role_name not in self._role_definitions:
            return []
        
        return [perm.value for perm in self._role_definitions[role_name].permissions]
    
    def get_all_roles(self) -> Dict[str, Dict[str, Any]]:
        """
        全ロールの情報を取得
        
        Returns:
            ロール情報の辞書
        """
        return {
            name: {
                "name": role_def.name,
                "description": role_def.description,
                "permissions": [perm.value for perm in role_def.permissions],
                "inherits_from": role_def.inherits_from
            }
            for name, role_def in self._role_definitions.items()
        }
    
    def clear_user_permissions(self, user_id: str):
        """
        ユーザーの全権限をクリア
        
        Args:
            user_id: ユーザーID
        """
        if user_id in self._user_roles:
            del self._user_roles[user_id]
        
        if user_id in self._user_permissions:
            del self._user_permissions[user_id]
        
        logger.info(f"All permissions cleared for user {user_id}")