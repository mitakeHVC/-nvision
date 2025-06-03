"""
顧客管理エンドポイント

顧客データの CRUD 操作と検索機能を提供します。
認証・認可システムで保護されています。
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from fastapi.responses import JSONResponse

from ....auth.dependencies import (
    get_current_active_user, require_permission, get_pagination_params, get_sort_params
)
from ....auth.permissions import Permission
from ....auth.decorators import require_permissions, audit_log, rate_limit
from ....auth.auth_service import AuthUser
from ....data_models.crm_models import Customer, CustomerCreate, CustomerUpdate
from ....services.customer_service import CustomerService
from ....repositories.customer_repository import CustomerRepository
from ...exceptions import NotFoundError, AuthorizationError, handle_exceptions

router = APIRouter()


# === 依存性 ===

def get_customer_service() -> CustomerService:
    """顧客サービスを取得"""
    # 実際の実装では、依存性注入でサービスを取得
    customer_repository = CustomerRepository(connection_manager=None)
    return CustomerService(customer_repository)


# === 顧客CRUD エンドポイント ===

@router.get("/", response_model=List[Customer], summary="顧客一覧取得")
@handle_exceptions("Failed to get customers")
async def get_customers(
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_LIST)),
    customer_service: CustomerService = Depends(get_customer_service),
    pagination: dict = Depends(get_pagination_params),
    sort_params: dict = Depends(lambda: get_sort_params(
        allowed_fields=["customer_id", "name", "email", "created_at", "updated_at"]
    )),
    search: Optional[str] = Query(None, description="検索キーワード"),
    status: Optional[str] = Query(None, description="顧客ステータス"),
    segment: Optional[str] = Query(None, description="顧客セグメント")
):
    """
    顧客一覧を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        pagination: ページネーションパラメータ
        sort_params: ソートパラメータ
        search: 検索キーワード
        status: 顧客ステータス
        segment: 顧客セグメント
        
    Returns:
        顧客一覧
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_LIST
    """
    # 検索条件を構築
    filters = {}
    if search:
        filters["search"] = search
    if status:
        filters["status"] = status
    if segment:
        filters["segment"] = segment
    
    # 顧客一覧を取得
    customers = await customer_service.get_customers(
        page=pagination["page"],
        per_page=pagination["per_page"],
        sort_by=sort_params["sort_by"],
        sort_order=sort_params["sort_order"],
        filters=filters
    )
    
    return customers


@router.get("/{customer_id}", response_model=Customer, summary="顧客詳細取得")
@handle_exceptions("Failed to get customer")
async def get_customer(
    customer_id: str = Path(..., description="顧客ID"),
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_READ)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    顧客詳細を取得
    
    Args:
        customer_id: 顧客ID
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Returns:
        顧客詳細
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_READ
        
    Raises:
        NotFoundError: 顧客が見つからない場合
    """
    customer = await customer_service.get_customer_by_id(customer_id)
    
    if not customer:
        raise NotFoundError("Customer")
    
    return customer


@router.post("/", response_model=Customer, status_code=status.HTTP_201_CREATED, summary="顧客作成")
@handle_exceptions("Failed to create customer")
async def create_customer(
    customer_data: CustomerCreate,
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_CREATE)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    新規顧客を作成
    
    Args:
        customer_data: 顧客作成データ
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Returns:
        作成された顧客
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_CREATE
    """
    customer = await customer_service.create_customer(
        customer_data=customer_data,
        created_by=current_user.user_id
    )
    
    return customer


@router.put("/{customer_id}", response_model=Customer, summary="顧客更新")
@handle_exceptions("Failed to update customer")
async def update_customer(
    customer_id: str = Path(..., description="顧客ID"),
    customer_data: CustomerUpdate = ...,
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_UPDATE)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    顧客情報を更新
    
    Args:
        customer_id: 顧客ID
        customer_data: 顧客更新データ
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Returns:
        更新された顧客
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_UPDATE
        
    Raises:
        NotFoundError: 顧客が見つからない場合
    """
    customer = await customer_service.update_customer(
        customer_id=customer_id,
        customer_data=customer_data,
        updated_by=current_user.user_id
    )
    
    if not customer:
        raise NotFoundError("Customer")
    
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="顧客削除")
@handle_exceptions("Failed to delete customer")
async def delete_customer(
    customer_id: str = Path(..., description="顧客ID"),
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_DELETE)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    顧客を削除
    
    Args:
        customer_id: 顧客ID
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_DELETE
        
    Raises:
        NotFoundError: 顧客が見つからない場合
    """
    success = await customer_service.delete_customer(
        customer_id=customer_id,
        deleted_by=current_user.user_id
    )
    
    if not success:
        raise NotFoundError("Customer")


# === 顧客検索エンドポイント ===

@router.get("/search/advanced", response_model=List[Customer], summary="高度な顧客検索")
@handle_exceptions("Failed to search customers")
async def advanced_customer_search(
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_LIST)),
    customer_service: CustomerService = Depends(get_customer_service),
    query: Optional[str] = Query(None, description="検索クエリ"),
    name: Optional[str] = Query(None, description="顧客名"),
    email: Optional[str] = Query(None, description="メールアドレス"),
    phone: Optional[str] = Query(None, description="電話番号"),
    status: Optional[str] = Query(None, description="ステータス"),
    segment: Optional[str] = Query(None, description="セグメント"),
    created_after: Optional[str] = Query(None, description="作成日時（以降）"),
    created_before: Optional[str] = Query(None, description="作成日時（以前）"),
    pagination: dict = Depends(get_pagination_params)
):
    """
    高度な顧客検索
    
    Args:
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        query: 検索クエリ
        name: 顧客名
        email: メールアドレス
        phone: 電話番号
        status: ステータス
        segment: セグメント
        created_after: 作成日時（以降）
        created_before: 作成日時（以前）
        pagination: ページネーションパラメータ
        
    Returns:
        検索結果
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_LIST
    """
    # 検索条件を構築
    search_criteria = {}
    if query:
        search_criteria["query"] = query
    if name:
        search_criteria["name"] = name
    if email:
        search_criteria["email"] = email
    if phone:
        search_criteria["phone"] = phone
    if status:
        search_criteria["status"] = status
    if segment:
        search_criteria["segment"] = segment
    if created_after:
        search_criteria["created_after"] = created_after
    if created_before:
        search_criteria["created_before"] = created_before
    
    # 検索実行
    customers = await customer_service.search_customers(
        criteria=search_criteria,
        page=pagination["page"],
        per_page=pagination["per_page"]
    )
    
    return customers


# === 顧客統計エンドポイント ===

@router.get("/stats/overview", summary="顧客統計概要")
@handle_exceptions("Failed to get customer statistics")
async def get_customer_statistics(
    current_user: AuthUser = Depends(require_permission(Permission.ANALYTICS_READ)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    顧客統計概要を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Returns:
        顧客統計
        
    Requires:
        - 認証: 必須
        - 権限: ANALYTICS_READ
    """
    stats = await customer_service.get_customer_statistics()
    
    return {
        "total_customers": stats.get("total", 0),
        "active_customers": stats.get("active", 0),
        "new_customers_this_month": stats.get("new_this_month", 0),
        "customer_segments": stats.get("segments", {}),
        "top_customers": stats.get("top_customers", [])
    }


# === 顧客セグメントエンドポイント ===

@router.get("/{customer_id}/segment", summary="顧客セグメント取得")
@handle_exceptions("Failed to get customer segment")
async def get_customer_segment(
    customer_id: str = Path(..., description="顧客ID"),
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_READ)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    顧客セグメントを取得
    
    Args:
        customer_id: 顧客ID
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Returns:
        顧客セグメント情報
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_READ
    """
    segment = await customer_service.get_customer_segment(customer_id)
    
    if not segment:
        raise NotFoundError("Customer segment")
    
    return segment


@router.put("/{customer_id}/segment", summary="顧客セグメント更新")
@handle_exceptions("Failed to update customer segment")
async def update_customer_segment(
    customer_id: str = Path(..., description="顧客ID"),
    segment_data: dict = ...,
    current_user: AuthUser = Depends(require_permission(Permission.CUSTOMER_UPDATE)),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    顧客セグメントを更新
    
    Args:
        customer_id: 顧客ID
        segment_data: セグメントデータ
        current_user: 現在のユーザー（認証済み）
        customer_service: 顧客サービス
        
    Returns:
        更新されたセグメント情報
        
    Requires:
        - 認証: 必須
        - 権限: CUSTOMER_UPDATE
    """
    segment = await customer_service.update_customer_segment(
        customer_id=customer_id,
        segment_data=segment_data,
        updated_by=current_user.user_id
    )
    
    if not segment:
        raise NotFoundError("Customer")
    
    return segment