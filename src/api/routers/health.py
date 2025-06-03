"""
ヘルスチェックルーター

システムの健全性をチェックするエンドポイントを提供します。
"""

import time
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..exceptions import ServiceUnavailableError
from ...config.auth_config import get_auth_settings

router = APIRouter()
auth_settings = get_auth_settings()


@router.get("/", summary="基本ヘルスチェック")
async def health_check() -> Dict[str, Any]:
    """
    基本的なヘルスチェック
    
    Returns:
        システムの基本状態
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "service": "nvision-api"
    }


@router.get("/detailed", summary="詳細ヘルスチェック")
async def detailed_health_check() -> Dict[str, Any]:
    """
    詳細なヘルスチェック
    
    Returns:
        システムの詳細状態
    """
    try:
        # システムリソース情報
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # プロセス情報
        process = psutil.Process()
        process_memory = process.memory_info()
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "service": "nvision-api",
            "uptime": time.time() - process.create_time(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "used": disk.used,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "process": {
                "pid": process.pid,
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads()
            }
        }
        
        # 健全性判定
        if cpu_percent > 90:
            health_data["status"] = "degraded"
            health_data["warnings"] = health_data.get("warnings", [])
            health_data["warnings"].append("High CPU usage")
        
        if memory.percent > 90:
            health_data["status"] = "degraded"
            health_data["warnings"] = health_data.get("warnings", [])
            health_data["warnings"].append("High memory usage")
        
        if (disk.used / disk.total) * 100 > 90:
            health_data["status"] = "degraded"
            health_data["warnings"] = health_data.get("warnings", [])
            health_data["warnings"].append("High disk usage")
        
        return health_data
        
    except Exception as e:
        raise ServiceUnavailableError(
            message="Health check failed",
            details={"error": str(e)}
        )


@router.get("/ready", summary="レディネスチェック")
async def readiness_check() -> Dict[str, Any]:
    """
    レディネスチェック（サービスがリクエストを受け入れ可能か）
    
    Returns:
        サービスの準備状態
    """
    try:
        # 依存サービスの確認
        checks = {
            "database": await _check_database(),
            "cache": await _check_cache(),
            "external_services": await _check_external_services()
        }
        
        # 全てのチェックが成功しているか
        all_ready = all(checks.values())
        
        return {
            "status": "ready" if all_ready else "not_ready",
            "timestamp": time.time(),
            "checks": checks
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@router.get("/live", summary="ライブネスチェック")
async def liveness_check() -> Dict[str, Any]:
    """
    ライブネスチェック（サービスが生きているか）
    
    Returns:
        サービスの生存状態
    """
    return {
        "status": "alive",
        "timestamp": time.time(),
        "pid": psutil.Process().pid
    }


@router.get("/metrics", summary="メトリクス取得")
async def get_metrics() -> Dict[str, Any]:
    """
    システムメトリクスを取得
    
    Returns:
        システムメトリクス
    """
    if not auth_settings.debug_mode:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Not found"}
        )
    
    try:
        process = psutil.Process()
        
        return {
            "timestamp": time.time(),
            "metrics": {
                "cpu": {
                    "system_percent": psutil.cpu_percent(interval=1),
                    "process_percent": process.cpu_percent(),
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "system": psutil.virtual_memory()._asdict(),
                    "process": process.memory_info()._asdict()
                },
                "disk": psutil.disk_usage('/')._asdict(),
                "network": psutil.net_io_counters()._asdict(),
                "process": {
                    "pid": process.pid,
                    "ppid": process.ppid(),
                    "name": process.name(),
                    "status": process.status(),
                    "create_time": process.create_time(),
                    "num_threads": process.num_threads(),
                    "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None
                }
            }
        }
        
    except Exception as e:
        raise ServiceUnavailableError(
            message="Failed to get metrics",
            details={"error": str(e)}
        )


# === プライベート関数 ===

async def _check_database() -> bool:
    """データベース接続チェック"""
    try:
        # 実際の実装では、データベースへの接続テストを行う
        # ここではダミー実装
        return True
    except Exception:
        return False


async def _check_cache() -> bool:
    """キャッシュ接続チェック"""
    try:
        # 実際の実装では、Redis等のキャッシュへの接続テストを行う
        # ここではダミー実装
        return True
    except Exception:
        return False


async def _check_external_services() -> bool:
    """外部サービス接続チェック"""
    try:
        # 実際の実装では、外部APIへの接続テストを行う
        # ここではダミー実装
        return True
    except Exception:
        return False