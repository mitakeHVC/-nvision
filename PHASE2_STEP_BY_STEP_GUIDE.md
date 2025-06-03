# Phase 2 ステップバイステップ実装ガイド

## 📋 実装順序と詳細手順

### Step 1: CI/CD基盤構築 (推定: 3-4日)

#### 🎯 目標
自動テスト・デプロイ環境の確立による品質保証の自動化

#### 📝 実装内容

##### 1.1 GitHub Actions設定
**ファイル**: [`/.github/workflows/ci.yml`](.github/workflows/ci.yml)
```yaml
name: CI Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5.0
        env:
          NEO4J_AUTH: neo4j/password
        ports:
          - 7687:7687
          - 7474:7474
      
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest-cov black flake8 mypy
    
    - name: Code quality checks
      run: |
        black --check src tests
        flake8 src tests
        mypy src
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

**ファイル**: [`/.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
```yaml
name: Deploy Pipeline
on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build and deploy
      run: |
        docker-compose -f docker-compose.prod.yml build
        # デプロイロジック追加予定
```

##### 1.2 品質ゲート設定
**ファイル**: [`/pyproject.toml`](pyproject.toml)
```toml
[tool.black]
line-length = 88
target-version = ['py39']

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

**ファイル**: [`/.pre-commit-config.yaml`](.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
```

#### 🧪 テスト内容
- CI/CDパイプラインの動作確認
- 自動テスト実行の検証
- コード品質チェックの動作確認

#### 🔄 Git処理
```bash
git checkout -b feature/ci-cd-setup
git add .github/ pyproject.toml .pre-commit-config.yaml
git commit -m "feat: setup CI/CD pipeline with GitHub Actions"
git push origin feature/ci-cd-setup
# Pull Request作成 → レビュー → マージ
```

#### ✅ 完了条件
- [ ] GitHub Actionsが正常に動作
- [ ] 全テストが自動実行される
- [ ] コード品質チェックが機能
- [ ] プリコミットフックが動作

---

### Step 2: FastAPI基盤実装 (推定: 4-5日)

#### 🎯 目標
FastAPIアプリケーションの基本構造構築

#### 📝 実装内容

##### 2.1 FastAPIプロジェクト構造
**ファイル**: [`/src/api/__init__.py`](src/api/__init__.py)
```python
"""FastAPI application package."""
__version__ = "0.1.0"
```

**ファイル**: [`/src/api/main.py`](src/api/main.py)
```python
"""FastAPI application main module."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.middleware import LoggingMiddleware, ErrorHandlingMiddleware
from src.api.routers import health
from src.api.config import get_settings

settings = get_settings()

app = FastAPI(
    title="nvision API",
    description="Customer behavior analysis and AI/ML platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])

@app.get("/")
async def root():
    return {"message": "nvision API is running", "version": "0.1.0"}
```

**ファイル**: [`/src/api/dependencies.py`](src/api/dependencies.py)
```python
"""FastAPI dependencies."""
from typing import Generator
from src.database.neo4j_client import Neo4jClient
from src.database.chroma_client import ChromaClient
from src.api.config import get_settings

settings = get_settings()

def get_neo4j_client() -> Generator[Neo4jClient, None, None]:
    """Get Neo4j client dependency."""
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    try:
        yield client
    finally:
        client.close()

def get_chroma_client() -> Generator[ChromaClient, None, None]:
    """Get ChromaDB client dependency."""
    client = ChromaClient(settings.CHROMA_HOST, settings.CHROMA_PORT)
    try:
        yield client
    finally:
        client.close()
```

##### 2.2 基本設定・ミドルウェア
**ファイル**: [`/src/api/middleware.py`](src/api/middleware.py)
```python
"""FastAPI middleware implementations."""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(f"Unhandled error: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
```

**ファイル**: [`/src/api/config.py`](src/api/config.py)
```python
"""Application configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "nvision"
    
    # CORS Settings
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

##### 2.3 ヘルスチェック実装
**ファイル**: [`/src/api/routers/health.py`](src/api/routers/health.py)
```python
"""Health check endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from src.database.neo4j_client import Neo4jClient
from src.database.chroma_client import ChromaClient
from src.api.dependencies import get_neo4j_client, get_chroma_client

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "nvision-api"}

@router.get("/health/detailed")
async def detailed_health_check(
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
    chroma_client: ChromaClient = Depends(get_chroma_client)
):
    """Detailed health check including database connections."""
    health_status = {
        "status": "healthy",
        "services": {
            "api": "healthy",
            "neo4j": "unknown",
            "chroma": "unknown"
        }
    }
    
    # Check Neo4j
    try:
        neo4j_client.verify_connectivity()
        health_status["services"]["neo4j"] = "healthy"
    except Exception:
        health_status["services"]["neo4j"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check ChromaDB
    try:
        chroma_client.heartbeat()
        health_status["services"]["chroma"] = "healthy"
    except Exception:
        health_status["services"]["chroma"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status
```

#### 🧪 テスト内容
**ファイル**: [`/tests/api/test_main.py`](tests/api/test_main.py)
```python
"""Tests for FastAPI main application."""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "nvision API is running" in response.json()["message"]

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_docs_endpoint():
    """Test API documentation endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200
```

#### 🔄 Git処理
```bash
git checkout -b feature/fastapi-foundation
git add src/api/ tests/api/
git commit -m "feat: implement FastAPI foundation with basic middleware"
git push origin feature/fastapi-foundation
# Pull Request作成 → レビュー → マージ
```

#### ✅ 完了条件
- [ ] FastAPIアプリケーションが正常起動
- [ ] OpenAPI仕様書が自動生成される
- [ ] ヘルスチェックが機能
- [ ] ミドルウェアが正常動作

---

### Step 3: データアクセス層実装 (推定: 5-6日)

#### 🎯 目標
データベース接続とリポジトリパターンの実装

#### 📝 実装内容

##### 3.1 データベース接続層
**ファイル**: [`/src/database/neo4j_client.py`](src/database/neo4j_client.py)
```python
"""Neo4j database client."""
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver, Session
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    """Neo4j database client."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
    
    def verify_connectivity(self):
        """Verify database connectivity."""
        with self.driver.session() as session:
            result = session.run("RETURN 1 as test")
            return result.single()["test"] == 1
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a write Cypher query."""
        with self.driver.session() as session:
            result = session.write_transaction(self._execute_query, query, parameters or {})
            return result
    
    @staticmethod
    def _execute_query(tx, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute query within transaction."""
        result = tx.run(query, parameters)
        return [record.data() for record in result]
```

**ファイル**: [`/src/database/connection_manager.py`](src/database/connection_manager.py)
```python
"""Database connection manager."""
from typing import Optional
from contextlib import contextmanager
from src.database.neo4j_client import Neo4jClient
from src.database.chroma_client import ChromaClient
from src.api.config import get_settings

settings = get_settings()

class ConnectionManager:
    """Database connection manager."""
    
    def __init__(self):
        self._neo4j_client: Optional[Neo4jClient] = None
        self._chroma_client: Optional[ChromaClient] = None
    
    @property
    def neo4j(self) -> Neo4jClient:
        """Get Neo4j client."""
        if not self._neo4j_client:
            self._neo4j_client = Neo4jClient(
                settings.NEO4J_URI,
                settings.NEO4J_USER,
                settings.NEO4J_PASSWORD
            )
        return self._neo4j_client
    
    @property
    def chroma(self) -> ChromaClient:
        """Get ChromaDB client."""
        if not self._chroma_client:
            self._chroma_client = ChromaClient(
                settings.CHROMA_HOST,
                settings.CHROMA_PORT
            )
        return self._chroma_client
    
    def close_all(self):
        """Close all connections."""
        if self._neo4j_client:
            self._neo4j_client.close()
        if self._chroma_client:
            self._chroma_client.close()

# Global connection manager instance
connection_manager = ConnectionManager()

@contextmanager
def get_neo4j_session():
    """Get Neo4j session context manager."""
    try:
        yield connection_manager.neo4j
    except Exception as e:
        logger.error(f"Neo4j session error: {e}")
        raise

@contextmanager
def get_chroma_session():
    """Get ChromaDB session context manager."""
    try:
        yield connection_manager.chroma
    except Exception as e:
        logger.error(f"ChromaDB session error: {e}")
        raise
```

##### 3.2 リポジトリパターン実装
**ファイル**: [`/src/repositories/base_repository.py`](src/repositories/base_repository.py)
```python
"""Base repository class."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, TypeVar, Generic
from src.database.neo4j_client import Neo4jClient

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository class."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j_client = neo4j_client
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity."""
        pass
    
    @abstractmethod
    def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List entities with pagination."""
        pass
```

**ファイル**: [`/src/repositories/customer_repository.py`](src/repositories/customer_repository.py)
```python
"""Customer repository implementation."""
from typing import Dict, List, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.data_models.crm_models import Customer
from src.database.neo4j_client import Neo4jClient

class CustomerRepository(BaseRepository[Customer]):
    """Customer repository."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        super().__init__(neo4j_client)
    
    def create(self, customer: Customer) -> Customer:
        """Create a new customer."""
        query = """
        CREATE (c:Customer {
            customer_id: $customer_id,
            first_name: $first_name,
            last_name: $last_name,
            email: $email,
            phone: $phone,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN c
        """
        parameters = {
            "customer_id": customer.customer_id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "phone": customer.phone
        }
        
        result = self.neo4j_client.execute_write_query(query, parameters)
        return self._map_to_customer(result[0]["c"])
    
    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        query = "MATCH (c:Customer {customer_id: $customer_id}) RETURN c"
        result = self.neo4j_client.execute_query(query, {"customer_id": customer_id})
        
        if result:
            return self._map_to_customer(result[0]["c"])
        return None
    
    def update(self, customer_id: str, updates: Dict[str, Any]) -> Optional[Customer]:
        """Update customer."""
        set_clause = ", ".join([f"c.{key} = ${key}" for key in updates.keys()])
        query = f"""
        MATCH (c:Customer {{customer_id: $customer_id}})
        SET {set_clause}, c.updated_at = datetime()
        RETURN c
        """
        
        parameters = {"customer_id": customer_id, **updates}
        result = self.neo4j_client.execute_write_query(query, parameters)
        
        if result:
            return self._map_to_customer(result[0]["c"])
        return None
    
    def delete(self, customer_id: str) -> bool:
        """Delete customer."""
        query = "MATCH (c:Customer {customer_id: $customer_id}) DELETE c"
        self.neo4j_client.execute_write_query(query, {"customer_id": customer_id})
        return True
    
    def list(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """List customers with pagination."""
        query = """
        MATCH (c:Customer)
        RETURN c
        ORDER BY c.created_at DESC
        SKIP $offset
        LIMIT $limit
        """
        
        result = self.neo4j_client.execute_query(query, {"limit": limit, "offset": offset})
        return [self._map_to_customer(record["c"]) for record in result]
    
    def search_by_email(self, email: str) -> List[Customer]:
        """Search customers by email."""
        query = """
        MATCH (c:Customer)
        WHERE c.email CONTAINS $email
        RETURN c
        ORDER BY c.created_at DESC
        """
        
        result = self.neo4j_client.execute_query(query, {"email": email})
        return [self._map_to_customer(record["c"]) for record in result]
    
    def _map_to_customer(self, node_data: Dict[str, Any]) -> Customer:
        """Map Neo4j node data to Customer model."""
        return Customer(
            customer_id=node_data["customer_id"],
            first_name=node_data["first_name"],
            last_name=node_data["last_name"],
            email=node_data["email"],
            phone=node_data.get("phone"),
            created_at=node_data.get("created_at"),
            updated_at=node_data.get("updated_at")
        )
```

##### 3.3 サービス層基盤
**ファイル**: [`/src/services/base_service.py`](src/services/base_service.py)
```python
"""Base service class."""
from abc import ABC
from src.database.connection_manager import ConnectionManager

class BaseService(ABC):
    """Base service class."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    @property
    def neo4j(self):
        """Get Neo4j client."""
        return self.connection_manager.neo4j
    
    @property
    def chroma(self):
        """Get ChromaDB client."""
        return self.connection_manager.chroma
```

**ファイル**: [`/src/services/data_service.py`](src/services/data_service.py)
```python
"""Data access service."""
from typing import Dict, List, Any, Optional
from src.services.base_service import BaseService
from src.repositories.customer_repository import CustomerRepository
from src.repositories.product_repository import ProductRepository
from src.data_models.crm_models import Customer
from src.data_models.ec_models import Product

class DataService(BaseService):
    """Data access service."""
    
    def __init__(self, connection_manager):
        super().__init__(connection_manager)
        self.customer_repo = CustomerRepository(self.neo4j)
        self.product_repo = ProductRepository(self.neo4j)
    
    # Customer operations
    def create_customer(self, customer: Customer) -> Customer:
        """Create a new customer."""
        return self.customer_repo.create(customer)
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        return self.customer_repo.get_by_id(customer_id)
    
    def update_customer(self, customer_id: str, updates: Dict[str, Any]) -> Optional[Customer]:
        """Update customer."""
        return self.customer_repo.update(customer_id, updates)
    
    def delete_customer(self, customer_id: str) -> bool:
        """Delete customer."""
        return self.customer_repo.delete(customer_id)
    
    def list_customers(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """List customers."""
        return self.customer_repo.list(limit, offset)
    
    def search_customers_by_email(self, email: str) -> List[Customer]:
        """Search customers by email."""
        return self.customer_repo.search_by_email(email)
    
    # Product operations
    def create_product(self, product: Product) -> Product:
        """Create a new product."""
        return self.product_repo.create(product)
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self.product_repo.get_by_id(product_id)
    
    def list_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """List products."""
        return self.product_repo.list(limit, offset)
```

#### 🧪 テスト内容
**ファイル**: [`/tests/repositories/test_customer_repository.py`](tests/repositories/test_customer_repository.py)
```python
"""Tests for customer repository."""
import pytest
from unittest.mock import Mock, MagicMock
from src.repositories.customer_repository import CustomerRepository
from src.data_models.crm_models import Customer

@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    return Mock()

@pytest.fixture
def customer_repo(mock_neo4j_client):
    """Customer repository fixture."""
    return CustomerRepository(mock_neo4j_client)

@pytest.fixture
def sample_customer():
    """Sample customer fixture."""
    return Customer(
        customer_id="test-123",
        first_name="Test",
        last_name="User",
        email="test@example.com",
        phone="123-456-7890"
    )

def test_create_customer(customer_repo, mock_neo4j_client, sample_customer):
    """Test customer creation."""
    # Mock the database response
    mock_neo4j_client.execute_write_query.return_value = [
        {"c": {
            "customer_id": "test-123",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "123-456-7890"
        }}
    ]
    
    result = customer_repo.create(sample_customer)
    
    assert result.customer_id == "test-123"
    assert result.email == "test@example.com"
    mock_neo4j_client.execute_write_query.assert_called_once()

def test_get_customer_by_id(customer_repo, mock_neo4j_client):
    """Test get customer by ID."""
    mock_neo4j_client.execute_query.return_value = [
        {"c": {
            "customer_id": "test-123",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com"
        }}
    ]
    
    result = customer_repo.get_by_id("test-123")
    
    assert result is not None
    assert result.customer_id == "test-123"
    mock_neo4j_client.execute_query.assert_called_once()

def test_get_customer_not_found(customer_repo, mock_neo4j_client):
    """Test get customer when not found."""
    mock_neo4j_client.execute_query.return_value = []
    
    result = customer_repo.get_by_id("nonexistent")
    
    assert result is None
```

#### 🔄 Git処理
```bash
git checkout -b feature/data-access-layer
git add src/database/ src/repositories/ src/services/ tests/repositories/
git commit -m "feat: implement data access layer with repository pattern"
git push origin feature/data-access-layer
# Pull Request作成 → レビュー → マージ
```

#### ✅ 完了条件
- [ ] Neo4j・ChromaDB接続が安定
- [ ] CRUD操作が正常動作
- [ ] データアクセスパフォーマンスが基準値内
- [ ] リポジトリパターンが適切に実装

---

### 継続実装ステップ

この文書では最初の3ステップの詳細を示しました。残りのステップ（Step 4-7）については、これらの基盤が完成した後に詳細化します。

#### 次のステップ概要
- **Step 4**: 認証・認可システム（JWT、ユーザー管理）
- **Step 5**: コアAPI実装（CRUD、検索、レコメンデーション）
- **Step 6**: 統合・最適化（キャッシュ、エラーハンドリング）
- **Step 7**: ドキュメント・デプロイ（API仕様書、運用準備）

各ステップの詳細実装ガイドは、前のステップ完了後に段階的に提供されます。