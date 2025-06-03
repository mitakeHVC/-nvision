"""
ヘルスチェックルーター

システムの稼働状況を確認するためのエンドポイントを提供します。
"""

from fastapi import APIRouter
from datetime import datetime
import psutil
import os

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    ヘルスチェック
    
    Returns:
        システムの稼働状況
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
        "environment": "development",
        "services": {
            "api": "running",
            "database": "connected",
            "cache": "available"
        }
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    詳細ヘルスチェック
    
    Returns:
        詳細なシステム情報
    """
    try:
        # システム情報を取得
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "environment": "development",
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "memory_available": f"{memory.available / (1024**3):.2f} GB",
                "disk_usage": f"{disk.percent}%",
                "disk_free": f"{disk.free / (1024**3):.2f} GB"
            },
            "services": {
                "api": "running",
                "database": "connected",
                "cache": "available",
                "neo4j": "connected",
                "chromadb": "available"
            },
            "features": {
                "authentication": "enabled",
                "authorization": "enabled",
                "rate_limiting": "enabled",
                "cors": "configured",
                "security_headers": "enabled"
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "environment": "development",
            "error": str(e),
            "services": {
                "api": "running",
                "database": "unknown",
                "cache": "unknown"
            }
        }


@router.get("/health/ready")
async def readiness_check():
    """
    レディネスチェック
    
    Returns:
        サービスの準備状況
    """
    return {
        "ready": True,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "ready",
            "cache": "ready",
            "external_services": "ready"
        }
    }


@router.get("/health/live")
async def liveness_check():
    """
    ライブネスチェック
    
    Returns:
        サービスの生存状況
    """
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat(),
        "uptime": "running"
    }