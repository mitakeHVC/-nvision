"""
商品管理エンドポイント

商品データの CRUD 操作と検索機能を提供します。
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
from ....data_models.ec_models import Product, ProductCreate, ProductUpdate
from ....services.product_service import ProductService
from ....repositories.product_repository import ProductRepository
from ...exceptions import NotFoundError, AuthorizationError, handle_exceptions

router = APIRouter()


# === 依存性 ===

def get_product_service() -> ProductService:
    """商品サービスを取得"""
    # 実際の実装では、依存性注入でサービスを取得
    product_repository = ProductRepository(connection_manager=None)
    return ProductService(product_repository)


# === 商品CRUD エンドポイント ===

@router.get("/", response_model=List[Product], summary="商品一覧取得")
@handle_exceptions("Failed to get products")
async def get_products(
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_LIST)),
    product_service: ProductService = Depends(get_product_service),
    pagination: dict = Depends(get_pagination_params),
    sort_params: dict = Depends(lambda: get_sort_params(
        allowed_fields=["product_id", "name", "price", "category", "created_at", "updated_at"]
    )),
    search: Optional[str] = Query(None, description="検索キーワード"),
    category: Optional[str] = Query(None, description="カテゴリ"),
    status: Optional[str] = Query(None, description="商品ステータス"),
    min_price: Optional[float] = Query(None, description="最小価格"),
    max_price: Optional[float] = Query(None, description="最大価格")
):
    """
    商品一覧を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        pagination: ページネーションパラメータ
        sort_params: ソートパラメータ
        search: 検索キーワード
        category: カテゴリ
        status: 商品ステータス
        min_price: 最小価格
        max_price: 最大価格
        
    Returns:
        商品一覧
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_LIST
    """
    # 検索条件を構築
    filters = {}
    if search:
        filters["search"] = search
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    if min_price is not None:
        filters["min_price"] = min_price
    if max_price is not None:
        filters["max_price"] = max_price
    
    # 商品一覧を取得
    products = await product_service.get_products(
        page=pagination["page"],
        per_page=pagination["per_page"],
        sort_by=sort_params["sort_by"],
        sort_order=sort_params["sort_order"],
        filters=filters
    )
    
    return products


@router.get("/{product_id}", response_model=Product, summary="商品詳細取得")
@handle_exceptions("Failed to get product")
async def get_product(
    product_id: str = Path(..., description="商品ID"),
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_READ)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品詳細を取得
    
    Args:
        product_id: 商品ID
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        商品詳細
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_READ
        
    Raises:
        NotFoundError: 商品が見つからない場合
    """
    product = await product_service.get_product_by_id(product_id)
    
    if not product:
        raise NotFoundError("Product")
    
    return product


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED, summary="商品作成")
@handle_exceptions("Failed to create product")
async def create_product(
    product_data: ProductCreate,
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_CREATE)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    新規商品を作成
    
    Args:
        product_data: 商品作成データ
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        作成された商品
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_CREATE
    """
    product = await product_service.create_product(
        product_data=product_data,
        created_by=current_user.user_id
    )
    
    return product


@router.put("/{product_id}", response_model=Product, summary="商品更新")
@handle_exceptions("Failed to update product")
async def update_product(
    product_id: str = Path(..., description="商品ID"),
    product_data: ProductUpdate = ...,
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_UPDATE)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品情報を更新
    
    Args:
        product_id: 商品ID
        product_data: 商品更新データ
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        更新された商品
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_UPDATE
        
    Raises:
        NotFoundError: 商品が見つからない場合
    """
    product = await product_service.update_product(
        product_id=product_id,
        product_data=product_data,
        updated_by=current_user.user_id
    )
    
    if not product:
        raise NotFoundError("Product")
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="商品削除")
@handle_exceptions("Failed to delete product")
async def delete_product(
    product_id: str = Path(..., description="商品ID"),
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_DELETE)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品を削除
    
    Args:
        product_id: 商品ID
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_DELETE
        
    Raises:
        NotFoundError: 商品が見つからない場合
    """
    success = await product_service.delete_product(
        product_id=product_id,
        deleted_by=current_user.user_id
    )
    
    if not success:
        raise NotFoundError("Product")


# === 商品検索エンドポイント ===

@router.get("/search/advanced", response_model=List[Product], summary="高度な商品検索")
@handle_exceptions("Failed to search products")
async def advanced_product_search(
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_LIST)),
    product_service: ProductService = Depends(get_product_service),
    query: Optional[str] = Query(None, description="検索クエリ"),
    name: Optional[str] = Query(None, description="商品名"),
    description: Optional[str] = Query(None, description="商品説明"),
    category: Optional[str] = Query(None, description="カテゴリ"),
    brand: Optional[str] = Query(None, description="ブランド"),
    status: Optional[str] = Query(None, description="ステータス"),
    min_price: Optional[float] = Query(None, description="最小価格"),
    max_price: Optional[float] = Query(None, description="最大価格"),
    in_stock: Optional[bool] = Query(None, description="在庫あり"),
    created_after: Optional[str] = Query(None, description="作成日時（以降）"),
    created_before: Optional[str] = Query(None, description="作成日時（以前）"),
    pagination: dict = Depends(get_pagination_params)
):
    """
    高度な商品検索
    
    Args:
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        query: 検索クエリ
        name: 商品名
        description: 商品説明
        category: カテゴリ
        brand: ブランド
        status: ステータス
        min_price: 最小価格
        max_price: 最大価格
        in_stock: 在庫あり
        created_after: 作成日時（以降）
        created_before: 作成日時（以前）
        pagination: ページネーションパラメータ
        
    Returns:
        検索結果
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_LIST
    """
    # 検索条件を構築
    search_criteria = {}
    if query:
        search_criteria["query"] = query
    if name:
        search_criteria["name"] = name
    if description:
        search_criteria["description"] = description
    if category:
        search_criteria["category"] = category
    if brand:
        search_criteria["brand"] = brand
    if status:
        search_criteria["status"] = status
    if min_price is not None:
        search_criteria["min_price"] = min_price
    if max_price is not None:
        search_criteria["max_price"] = max_price
    if in_stock is not None:
        search_criteria["in_stock"] = in_stock
    if created_after:
        search_criteria["created_after"] = created_after
    if created_before:
        search_criteria["created_before"] = created_before
    
    # 検索実行
    products = await product_service.search_products(
        criteria=search_criteria,
        page=pagination["page"],
        per_page=pagination["per_page"]
    )
    
    return products


# === 商品統計エンドポイント ===

@router.get("/stats/overview", summary="商品統計概要")
@handle_exceptions("Failed to get product statistics")
async def get_product_statistics(
    current_user: AuthUser = Depends(require_permission(Permission.ANALYTICS_READ)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品統計概要を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        商品統計
        
    Requires:
        - 認証: 必須
        - 権限: ANALYTICS_READ
    """
    stats = await product_service.get_product_statistics()
    
    return {
        "total_products": stats.get("total", 0),
        "active_products": stats.get("active", 0),
        "out_of_stock": stats.get("out_of_stock", 0),
        "categories": stats.get("categories", {}),
        "top_selling": stats.get("top_selling", []),
        "average_price": stats.get("average_price", 0)
    }


# === 商品カテゴリエンドポイント ===

@router.get("/categories", summary="商品カテゴリ一覧")
@handle_exceptions("Failed to get product categories")
async def get_product_categories(
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_READ)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品カテゴリ一覧を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        カテゴリ一覧
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_READ
    """
    categories = await product_service.get_product_categories()
    
    return {
        "categories": categories
    }


# === 商品在庫エンドポイント ===

@router.get("/{product_id}/inventory", summary="商品在庫情報取得")
@handle_exceptions("Failed to get product inventory")
async def get_product_inventory(
    product_id: str = Path(..., description="商品ID"),
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_READ)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品在庫情報を取得
    
    Args:
        product_id: 商品ID
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        在庫情報
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_READ
    """
    inventory = await product_service.get_product_inventory(product_id)
    
    if not inventory:
        raise NotFoundError("Product inventory")
    
    return inventory


@router.put("/{product_id}/inventory", summary="商品在庫更新")
@handle_exceptions("Failed to update product inventory")
async def update_product_inventory(
    product_id: str = Path(..., description="商品ID"),
    inventory_data: dict = ...,
    current_user: AuthUser = Depends(require_permission(Permission.PRODUCT_UPDATE)),
    product_service: ProductService = Depends(get_product_service)
):
    """
    商品在庫を更新
    
    Args:
        product_id: 商品ID
        inventory_data: 在庫データ
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        
    Returns:
        更新された在庫情報
        
    Requires:
        - 認証: 必須
        - 権限: PRODUCT_UPDATE
    """
    inventory = await product_service.update_product_inventory(
        product_id=product_id,
        inventory_data=inventory_data,
        updated_by=current_user.user_id
    )
    
    if not inventory:
        raise NotFoundError("Product")
    
    return inventory


# === 商品レコメンデーションエンドポイント ===

@router.get("/{product_id}/recommendations", summary="商品レコメンデーション")
@handle_exceptions("Failed to get product recommendations")
async def get_product_recommendations(
    product_id: str = Path(..., description="商品ID"),
    current_user: AuthUser = Depends(require_permission(Permission.RECOMMENDATION_READ)),
    product_service: ProductService = Depends(get_product_service),
    limit: int = Query(10, description="取得件数", ge=1, le=50)
):
    """
    商品レコメンデーションを取得
    
    Args:
        product_id: 商品ID
        current_user: 現在のユーザー（認証済み）
        product_service: 商品サービス
        limit: 取得件数
        
    Returns:
        レコメンデーション結果
        
    Requires:
        - 認証: 必須
        - 権限: RECOMMENDATION_READ
    """
    recommendations = await product_service.get_product_recommendations(
        product_id=product_id,
        limit=limit
    )
    
    return {
        "product_id": product_id,
        "recommendations": recommendations
    }