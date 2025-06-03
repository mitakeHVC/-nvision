"""
検索エンドポイント

ベクトル検索、セマンティック検索、高度な検索機能を提供します。
認証・認可システムで保護されています。
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from ....auth.dependencies import (
    get_current_active_user, require_permission, get_pagination_params
)
from ....auth.permissions import Permission
from ....auth.decorators import require_permissions, audit_log, rate_limit
from ....auth.auth_service import AuthUser
from ....services.vector_search_service import VectorSearchService
from ....repositories.vector_repository import VectorRepository
from ...exceptions import ValidationError, handle_exceptions

router = APIRouter()


# === 依存性 ===

def get_vector_search_service() -> VectorSearchService:
    """ベクトル検索サービスを取得"""
    # 実際の実装では、依存性注入でサービスを取得
    vector_repository = VectorRepository(connection_manager=None)
    return VectorSearchService(vector_repository)


# === ベクトル検索エンドポイント ===

@router.post("/vector", summary="ベクトル検索")
@handle_exceptions("Vector search failed")
async def vector_search(
    query: str = Query(..., description="検索クエリ"),
    current_user: AuthUser = Depends(require_permission(Permission.SEARCH_VECTOR)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    collection_name: Optional[str] = Query("default", description="コレクション名"),
    top_k: int = Query(10, description="取得件数", ge=1, le=100),
    threshold: Optional[float] = Query(None, description="類似度閾値", ge=0.0, le=1.0),
    include_metadata: bool = Query(True, description="メタデータを含める"),
    include_distances: bool = Query(True, description="距離を含める")
):
    """
    ベクトル検索を実行
    
    Args:
        query: 検索クエリ
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        collection_name: コレクション名
        top_k: 取得件数
        threshold: 類似度閾値
        include_metadata: メタデータを含める
        include_distances: 距離を含める
        
    Returns:
        検索結果
        
    Requires:
        - 認証: 必須
        - 権限: SEARCH_VECTOR
        
    Raises:
        ValidationError: クエリが無効な場合
    """
    if not query.strip():
        raise ValidationError("Search query cannot be empty")
    
    # ベクトル検索実行
    results = await vector_search_service.search(
        query=query,
        collection_name=collection_name,
        top_k=top_k,
        threshold=threshold,
        include_metadata=include_metadata,
        include_distances=include_distances
    )
    
    return {
        "query": query,
        "collection": collection_name,
        "total_results": len(results),
        "results": results,
        "search_params": {
            "top_k": top_k,
            "threshold": threshold,
            "include_metadata": include_metadata,
            "include_distances": include_distances
        }
    }


@router.post("/semantic", summary="セマンティック検索")
@handle_exceptions("Semantic search failed")
async def semantic_search(
    query: str = Query(..., description="検索クエリ"),
    current_user: AuthUser = Depends(require_permission(Permission.SEARCH_SEMANTIC)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    collections: Optional[List[str]] = Query(None, description="検索対象コレクション"),
    top_k: int = Query(10, description="取得件数", ge=1, le=100),
    rerank: bool = Query(True, description="再ランキングを行う"),
    expand_query: bool = Query(True, description="クエリ拡張を行う"),
    filter_metadata: Optional[Dict[str, Any]] = None
):
    """
    セマンティック検索を実行
    
    Args:
        query: 検索クエリ
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        collections: 検索対象コレクション
        top_k: 取得件数
        rerank: 再ランキングを行う
        expand_query: クエリ拡張を行う
        filter_metadata: メタデータフィルター
        
    Returns:
        検索結果
        
    Requires:
        - 認証: 必須
        - 権限: SEARCH_SEMANTIC
        
    Raises:
        ValidationError: クエリが無効な場合
    """
    if not query.strip():
        raise ValidationError("Search query cannot be empty")
    
    # セマンティック検索実行
    results = await vector_search_service.semantic_search(
        query=query,
        collections=collections or ["default"],
        top_k=top_k,
        rerank=rerank,
        expand_query=expand_query,
        filter_metadata=filter_metadata
    )
    
    return {
        "query": query,
        "expanded_query": results.get("expanded_query"),
        "collections": collections or ["default"],
        "total_results": len(results.get("results", [])),
        "results": results.get("results", []),
        "search_params": {
            "top_k": top_k,
            "rerank": rerank,
            "expand_query": expand_query,
            "filter_metadata": filter_metadata
        },
        "search_time": results.get("search_time", 0)
    }


@router.post("/advanced", summary="高度な検索")
@handle_exceptions("Advanced search failed")
async def advanced_search(
    query: str = Query(..., description="検索クエリ"),
    current_user: AuthUser = Depends(require_permission(Permission.SEARCH_ADVANCED)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    search_type: str = Query("hybrid", description="検索タイプ", regex="^(vector|semantic|hybrid|fuzzy)$"),
    collections: Optional[List[str]] = Query(None, description="検索対象コレクション"),
    top_k: int = Query(10, description="取得件数", ge=1, le=100),
    filters: Optional[Dict[str, Any]] = None,
    boost_fields: Optional[Dict[str, float]] = None,
    include_similar: bool = Query(False, description="類似結果を含める"),
    pagination: dict = Depends(get_pagination_params)
):
    """
    高度な検索を実行
    
    Args:
        query: 検索クエリ
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        search_type: 検索タイプ
        collections: 検索対象コレクション
        top_k: 取得件数
        filters: フィルター条件
        boost_fields: ブーストフィールド
        include_similar: 類似結果を含める
        pagination: ページネーションパラメータ
        
    Returns:
        検索結果
        
    Requires:
        - 認証: 必須
        - 権限: SEARCH_ADVANCED
        
    Raises:
        ValidationError: パラメータが無効な場合
    """
    if not query.strip():
        raise ValidationError("Search query cannot be empty")
    
    # 高度な検索実行
    results = await vector_search_service.advanced_search(
        query=query,
        search_type=search_type,
        collections=collections or ["default"],
        top_k=top_k,
        filters=filters,
        boost_fields=boost_fields,
        include_similar=include_similar,
        page=pagination["page"],
        per_page=pagination["per_page"]
    )
    
    return {
        "query": query,
        "search_type": search_type,
        "collections": collections or ["default"],
        "total_results": results.get("total", 0),
        "results": results.get("results", []),
        "similar_queries": results.get("similar_queries", []) if include_similar else [],
        "facets": results.get("facets", {}),
        "search_params": {
            "top_k": top_k,
            "filters": filters,
            "boost_fields": boost_fields,
            "include_similar": include_similar
        },
        "pagination": {
            "page": pagination["page"],
            "per_page": pagination["per_page"],
            "total_pages": results.get("total_pages", 0),
            "has_next": results.get("has_next", False),
            "has_prev": results.get("has_prev", False)
        },
        "search_time": results.get("search_time", 0)
    }


# === 検索候補エンドポイント ===

@router.get("/suggestions", summary="検索候補取得")
@handle_exceptions("Failed to get search suggestions")
async def get_search_suggestions(
    query: str = Query(..., description="検索クエリ", min_length=1),
    current_user: AuthUser = Depends(require_permission(Permission.SEARCH_VECTOR)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    limit: int = Query(5, description="候補数", ge=1, le=20),
    collection_name: Optional[str] = Query("default", description="コレクション名")
):
    """
    検索候補を取得
    
    Args:
        query: 検索クエリ
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        limit: 候補数
        collection_name: コレクション名
        
    Returns:
        検索候補
        
    Requires:
        - 認証: 必須
        - 権限: SEARCH_VECTOR
    """
    suggestions = await vector_search_service.get_search_suggestions(
        query=query,
        collection_name=collection_name,
        limit=limit
    )
    
    return {
        "query": query,
        "suggestions": suggestions
    }


# === 検索履歴エンドポイント ===

@router.get("/history", summary="検索履歴取得")
@handle_exceptions("Failed to get search history")
async def get_search_history(
    current_user: AuthUser = Depends(get_current_active_user),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    pagination: dict = Depends(get_pagination_params),
    search_type: Optional[str] = Query(None, description="検索タイプフィルター")
):
    """
    ユーザーの検索履歴を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        pagination: ページネーションパラメータ
        search_type: 検索タイプフィルター
        
    Returns:
        検索履歴
        
    Requires:
        - 認証: 必須
    """
    history = await vector_search_service.get_user_search_history(
        user_id=current_user.user_id,
        page=pagination["page"],
        per_page=pagination["per_page"],
        search_type=search_type
    )
    
    return {
        "user_id": current_user.user_id,
        "total_searches": history.get("total", 0),
        "history": history.get("history", []),
        "pagination": {
            "page": pagination["page"],
            "per_page": pagination["per_page"],
            "total_pages": history.get("total_pages", 0)
        }
    }


@router.delete("/history", summary="検索履歴削除")
@handle_exceptions("Failed to clear search history")
async def clear_search_history(
    current_user: AuthUser = Depends(get_current_active_user),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service)
):
    """
    ユーザーの検索履歴を削除
    
    Args:
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        
    Returns:
        削除結果
        
    Requires:
        - 認証: 必須
    """
    success = await vector_search_service.clear_user_search_history(
        user_id=current_user.user_id
    )
    
    return {
        "message": "Search history cleared successfully" if success else "Failed to clear search history",
        "success": success
    }


# === 検索統計エンドポイント ===

@router.get("/stats", summary="検索統計取得")
@handle_exceptions("Failed to get search statistics")
async def get_search_statistics(
    current_user: AuthUser = Depends(require_permission(Permission.ANALYTICS_READ)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    period: str = Query("7d", description="期間", regex="^(1d|7d|30d|90d)$")
):
    """
    検索統計を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        period: 統計期間
        
    Returns:
        検索統計
        
    Requires:
        - 認証: 必須
        - 権限: ANALYTICS_READ
    """
    stats = await vector_search_service.get_search_statistics(period=period)
    
    return {
        "period": period,
        "total_searches": stats.get("total_searches", 0),
        "unique_users": stats.get("unique_users", 0),
        "popular_queries": stats.get("popular_queries", []),
        "search_types": stats.get("search_types", {}),
        "average_response_time": stats.get("average_response_time", 0),
        "collections_usage": stats.get("collections_usage", {}),
        "daily_breakdown": stats.get("daily_breakdown", [])
    }


# === コレクション管理エンドポイント ===

@router.get("/collections", summary="コレクション一覧取得")
@handle_exceptions("Failed to get collections")
async def get_collections(
    current_user: AuthUser = Depends(require_permission(Permission.SEARCH_VECTOR)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service)
):
    """
    利用可能なコレクション一覧を取得
    
    Args:
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        
    Returns:
        コレクション一覧
        
    Requires:
        - 認証: 必須
        - 権限: SEARCH_VECTOR
    """
    collections = await vector_search_service.get_collections()
    
    return {
        "collections": collections
    }


@router.get("/collections/{collection_name}/info", summary="コレクション情報取得")
@handle_exceptions("Failed to get collection info")
async def get_collection_info(
    collection_name: str,
    current_user: AuthUser = Depends(require_permission(Permission.SEARCH_VECTOR)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service)
):
    """
    コレクション情報を取得
    
    Args:
        collection_name: コレクション名
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        
    Returns:
        コレクション情報
        
    Requires:
        - 認証: 必須
        - 権限: SEARCH_VECTOR
    """
    info = await vector_search_service.get_collection_info(collection_name)
    
    if not info:
        raise ValidationError(f"Collection '{collection_name}' not found")
    
    return {
        "collection_name": collection_name,
        "info": info
    }


# === 検索結果エクスポートエンドポイント ===

@router.post("/export", summary="検索結果エクスポート")
@handle_exceptions("Failed to export search results")
async def export_search_results(
    query: str = Query(..., description="検索クエリ"),
    current_user: AuthUser = Depends(require_permission(Permission.ANALYTICS_EXPORT)),
    vector_search_service: VectorSearchService = Depends(get_vector_search_service),
    format: str = Query("json", description="エクスポート形式", regex="^(json|csv|xlsx)$"),
    collection_name: Optional[str] = Query("default", description="コレクション名"),
    top_k: int = Query(100, description="取得件数", ge=1, le=1000)
):
    """
    検索結果をエクスポート
    
    Args:
        query: 検索クエリ
        current_user: 現在のユーザー（認証済み）
        vector_search_service: ベクトル検索サービス
        format: エクスポート形式
        collection_name: コレクション名
        top_k: 取得件数
        
    Returns:
        エクスポートされたデータ
        
    Requires:
        - 認証: 必須
        - 権限: ANALYTICS_EXPORT
    """
    # 検索実行
    results = await vector_search_service.search(
        query=query,
        collection_name=collection_name,
        top_k=top_k,
        include_metadata=True,
        include_distances=True
    )
    
    # エクスポート処理
    exported_data = await vector_search_service.export_search_results(
        results=results,
        format=format
    )
    
    return {
        "query": query,
        "collection": collection_name,
        "format": format,
        "total_results": len(results),
        "export_data": exported_data,
        "exported_at": vector_search_service.get_current_timestamp()
    }