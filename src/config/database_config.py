"""
データベース設定管理モジュール

ChromaDBとNeo4jの接続設定を管理します。
環境変数を使用して設定を外部化し、開発・本番環境での切り替えを容易にします。
"""

import os
from typing import Optional
try:
    # Pydantic v2
    from pydantic import BaseModel, Field
    from pydantic_settings import BaseSettings
    PYDANTIC_V2 = True
except ImportError:
    # Pydantic v1
    from pydantic import BaseSettings, Field
    PYDANTIC_V2 = False


class DatabaseConfig(BaseSettings):
    """データベース設定クラス"""
    
    # Neo4j設定
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4jデータベースのURI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4jユーザー名"
    )
    neo4j_password: str = Field(
        default="password",
        description="Neo4jパスワード"
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4jデータベース名"
    )
    
    # ChromaDB設定
    chroma_host: str = Field(
        default="localhost",
        description="ChromaDBホスト"
    )
    chroma_port: int = Field(
        default=8000,
        description="ChromaDBポート"
    )
    chroma_persist_directory: Optional[str] = Field(
        default="./chroma_data",
        description="ChromaDBデータ永続化ディレクトリ"
    )
    
    # ベクトル埋め込み設定
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="使用する埋め込みモデル名"
    )
    embedding_dimension: int = Field(
        default=384,
        description="埋め込みベクトルの次元数"
    )
    
    # コレクション設定
    products_collection_name: str = Field(
        default="products",
        description="製品データのコレクション名"
    )
    reviews_collection_name: str = Field(
        default="reviews",
        description="レビューデータのコレクション名"
    )
    crm_notes_collection_name: str = Field(
        default="crm_notes",
        description="CRMメモのコレクション名"
    )
    
    if PYDANTIC_V2:
        model_config = {
            "env_file": ".env",
            "env_prefix": "NVISION_",
            "case_sensitive": False
        }
    else:
        class Config:
            env_file = ".env"
            env_prefix = "NVISION_"
            case_sensitive = False


# グローバル設定インスタンス
db_config = DatabaseConfig()


def get_neo4j_config() -> dict:
    """Neo4j接続設定を取得"""
    return {
        "uri": db_config.neo4j_uri,
        "auth": (db_config.neo4j_user, db_config.neo4j_password),
        "database": db_config.neo4j_database
    }


def get_chroma_config() -> dict:
    """ChromaDB接続設定を取得"""
    return {
        "host": db_config.chroma_host,
        "port": db_config.chroma_port,
        "persist_directory": db_config.chroma_persist_directory
    }


def get_embedding_config() -> dict:
    """埋め込み設定を取得"""
    return {
        "model_name": db_config.embedding_model_name,
        "dimension": db_config.embedding_dimension
    }


def get_collection_names() -> dict:
    """コレクション名設定を取得"""
    return {
        "products": db_config.products_collection_name,
        "reviews": db_config.reviews_collection_name,
        "crm_notes": db_config.crm_notes_collection_name
    }