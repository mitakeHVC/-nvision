# Phase 2 テスト戦略とGit戦略

## 🧪 テスト戦略の詳細化

### テスト種類と実行タイミング

| テスト種類 | 実行タイミング | カバレッジ目標 | 実行時間目標 | 責任者 |
|------------|----------------|----------------|--------------|--------|
| 単体テスト | 各コミット時 | 90%以上 | 30秒以内 | 開発者 |
| 統合テスト | PR作成時 | 80%以上 | 2分以内 | CI/CD |
| E2Eテスト | マージ前 | 主要フロー100% | 5分以内 | CI/CD |
| パフォーマンステスト | リリース前 | 全API | 10分以内 | QA |
| セキュリティテスト | リリース前 | 全エンドポイント | 15分以内 | QA |

### テストカバレッジ目標

#### コンポーネント別カバレッジ
- **データモデル**: 95%以上
- **リポジトリ層**: 90%以上
- **サービス層**: 90%以上
- **API層**: 85%以上
- **ミドルウェア**: 80%以上
- **統合テスト**: 80%以上

#### 機能別カバレッジ
- **CRUD操作**: 100%
- **認証・認可**: 100%
- **検索機能**: 95%以上
- **エラーハンドリング**: 90%以上
- **パフォーマンス**: 主要エンドポイント100%

## 📋 テスト実装計画

### Step 1: CI/CD基盤構築時のテスト

#### 1.1 GitHub Actions設定テスト
**ファイル**: [`/.github/workflows/test-ci.yml`](.github/workflows/test-ci.yml)
```yaml
name: Test CI Pipeline
on:
  workflow_dispatch:  # Manual trigger for testing

jobs:
  test-pipeline:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Test pipeline setup
      run: echo "CI pipeline test successful"
    
    - name: Validate workflow syntax
      run: |
        # Validate YAML syntax
        python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

#### 1.2 品質ゲートテスト
**ファイル**: [`/tests/quality/test_code_quality.py`](tests/quality/test_code_quality.py)
```python
"""Code quality tests."""
import subprocess
import pytest

def test_black_formatting():
    """Test that code is properly formatted with black."""
    result = subprocess.run(
        ["black", "--check", "src", "tests"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Code formatting issues: {result.stdout}"

def test_flake8_linting():
    """Test that code passes flake8 linting."""
    result = subprocess.run(
        ["flake8", "src", "tests"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Linting issues: {result.stdout}"

def test_mypy_type_checking():
    """Test that code passes mypy type checking."""
    result = subprocess.run(
        ["mypy", "src"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Type checking issues: {result.stdout}"
```

### Step 2: FastAPI基盤実装時のテスト

#### 2.1 アプリケーション起動テスト
**ファイル**: [`/tests/api/test_application.py`](tests/api/test_application.py)
```python
"""Application startup and configuration tests."""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_application_startup():
    """Test that application starts successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "nvision API is running" in response.json()["message"]

def test_openapi_schema_generation():
    """Test that OpenAPI schema is generated correctly."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "nvision API"

def test_docs_endpoints():
    """Test that documentation endpoints are accessible."""
    # Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
    
    # ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200

def test_cors_middleware():
    """Test CORS middleware configuration."""
    response = client.options("/", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
```

#### 2.2 ミドルウェアテスト
**ファイル**: [`/tests/api/test_middleware.py`](tests/api/test_middleware.py)
```python
"""Middleware tests."""
import pytest
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_logging_middleware():
    """Test logging middleware functionality."""
    with patch('src.api.middleware.logger') as mock_logger:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        # Verify logging calls
        assert mock_logger.info.call_count >= 2  # Request and response logs
        assert "X-Process-Time" in response.headers

def test_error_handling_middleware():
    """Test error handling middleware."""
    # This would test a route that intentionally raises an exception
    # For now, we'll test that the middleware is properly configured
    assert hasattr(app, 'middleware_stack')

def test_process_time_header():
    """Test that process time header is added."""
    response = client.get("/api/v1/health")
    assert "X-Process-Time" in response.headers
    process_time = float(response.headers["X-Process-Time"])
    assert process_time >= 0
```

#### 2.3 設定テスト
**ファイル**: [`/tests/api/test_config.py`](tests/api/test_config.py)
```python
"""Configuration tests."""
import pytest
from src.api.config import Settings, get_settings

def test_settings_creation():
    """Test settings creation with default values."""
    settings = Settings()
    assert settings.PROJECT_NAME == "nvision"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.ALGORITHM == "HS256"

def test_settings_caching():
    """Test that settings are cached."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2  # Same instance due to lru_cache

def test_environment_variable_override():
    """Test that environment variables override defaults."""
    import os
    original_value = os.environ.get("PROJECT_NAME")
    
    try:
        os.environ["PROJECT_NAME"] = "test-nvision"
        # Clear the cache
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.PROJECT_NAME == "test-nvision"
    finally:
        if original_value:
            os.environ["PROJECT_NAME"] = original_value
        else:
            os.environ.pop("PROJECT_NAME", None)
        get_settings.cache_clear()
```

### Step 3: データアクセス層実装時のテスト

#### 3.1 データベース接続テスト
**ファイル**: [`/tests/database/test_neo4j_client.py`](tests/database/test_neo4j_client.py)
```python
"""Neo4j client tests."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.database.neo4j_client import Neo4jClient

@pytest.fixture
def mock_driver():
    """Mock Neo4j driver."""
    driver = Mock()
    session = Mock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver, session

def test_neo4j_client_initialization():
    """Test Neo4j client initialization."""
    with patch('src.database.neo4j_client.GraphDatabase.driver') as mock_driver:
        client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        mock_driver.assert_called_once_with(
            "bolt://localhost:7687", 
            auth=("neo4j", "password")
        )

def test_verify_connectivity(mock_driver):
    """Test connectivity verification."""
    driver, session = mock_driver
    
    # Mock successful connectivity test
    result = Mock()
    result.single.return_value = {"test": 1}
    session.run.return_value = result
    
    with patch('src.database.neo4j_client.GraphDatabase.driver', return_value=driver):
        client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        assert client.verify_connectivity() == True

def test_execute_query(mock_driver):
    """Test query execution."""
    driver, session = mock_driver
    
    # Mock query result
    record1 = Mock()
    record1.data.return_value = {"name": "John", "age": 30}
    record2 = Mock()
    record2.data.return_value = {"name": "Jane", "age": 25}
    
    result = Mock()
    result.__iter__.return_value = [record1, record2]
    session.run.return_value = result
    
    with patch('src.database.neo4j_client.GraphDatabase.driver', return_value=driver):
        client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        results = client.execute_query("MATCH (n) RETURN n")
        
        assert len(results) == 2
        assert results[0]["name"] == "John"
        assert results[1]["name"] == "Jane"

def test_execute_write_query(mock_driver):
    """Test write query execution."""
    driver, session = mock_driver
    
    # Mock transaction
    tx = Mock()
    tx.run.return_value = []
    session.write_transaction.return_value = []
    
    with patch('src.database.neo4j_client.GraphDatabase.driver', return_value=driver):
        client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        result = client.execute_write_query("CREATE (n:Person {name: $name})", {"name": "John"})
        
        session.write_transaction.assert_called_once()

def test_client_close(mock_driver):
    """Test client connection closing."""
    driver, session = mock_driver
    
    with patch('src.database.neo4j_client.GraphDatabase.driver', return_value=driver):
        client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        client.close()
        driver.close.assert_called_once()
```

#### 3.2 リポジトリテスト
**ファイル**: [`/tests/repositories/test_base_repository.py`](tests/repositories/test_base_repository.py)
```python
"""Base repository tests."""
import pytest
from abc import ABC
from unittest.mock import Mock
from src.repositories.base_repository import BaseRepository

class TestRepository(BaseRepository):
    """Test implementation of base repository."""
    
    def create(self, entity):
        return entity
    
    def get_by_id(self, entity_id):
        return {"id": entity_id}
    
    def update(self, entity_id, updates):
        return {"id": entity_id, **updates}
    
    def delete(self, entity_id):
        return True
    
    def list(self, limit=100, offset=0):
        return [{"id": i} for i in range(offset, offset + min(limit, 10))]

def test_base_repository_abstract():
    """Test that BaseRepository is abstract."""
    with pytest.raises(TypeError):
        BaseRepository(Mock())

def test_repository_implementation():
    """Test repository implementation."""
    mock_client = Mock()
    repo = TestRepository(mock_client)
    
    # Test create
    entity = {"name": "test"}
    result = repo.create(entity)
    assert result == entity
    
    # Test get_by_id
    result = repo.get_by_id("123")
    assert result["id"] == "123"
    
    # Test update
    result = repo.update("123", {"name": "updated"})
    assert result["id"] == "123"
    assert result["name"] == "updated"
    
    # Test delete
    result = repo.delete("123")
    assert result == True
    
    # Test list
    result = repo.list(5, 0)
    assert len(result) == 5
    assert result[0]["id"] == 0
```

#### 3.3 統合テスト
**ファイル**: [`/tests/integration/test_data_access_integration.py`](tests/integration/test_data_access_integration.py)
```python
"""Data access integration tests."""
import pytest
from unittest.mock import Mock, patch
from src.services.data_service import DataService
from src.database.connection_manager import ConnectionManager
from src.data_models.crm_models import Customer

@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    manager = Mock(spec=ConnectionManager)
    manager.neo4j = Mock()
    manager.chroma = Mock()
    return manager

@pytest.fixture
def data_service(mock_connection_manager):
    """Data service fixture."""
    return DataService(mock_connection_manager)

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

def test_data_service_customer_operations(data_service, sample_customer, mock_connection_manager):
    """Test data service customer operations."""
    # Mock repository responses
    with patch('src.services.data_service.CustomerRepository') as MockCustomerRepo:
        mock_repo = MockCustomerRepo.return_value
        mock_repo.create.return_value = sample_customer
        mock_repo.get_by_id.return_value = sample_customer
        mock_repo.list.return_value = [sample_customer]
        
        # Test create
        result = data_service.create_customer(sample_customer)
        assert result.customer_id == "test-123"
        mock_repo.create.assert_called_once_with(sample_customer)
        
        # Test get
        result = data_service.get_customer("test-123")
        assert result.customer_id == "test-123"
        mock_repo.get_by_id.assert_called_once_with("test-123")
        
        # Test list
        results = data_service.list_customers()
        assert len(results) == 1
        assert results[0].customer_id == "test-123"
        mock_repo.list.assert_called_once()

def test_data_service_error_handling(data_service, mock_connection_manager):
    """Test data service error handling."""
    with patch('src.services.data_service.CustomerRepository') as MockCustomerRepo:
        mock_repo = MockCustomerRepo.return_value
        mock_repo.get_by_id.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            data_service.get_customer("test-123")
        
        assert "Database error" in str(exc_info.value)
```

## 🔄 Git戦略の詳細化

### ブランチ戦略

#### ブランチ命名規則
```
main                    # 本番環境ブランチ
develop                 # 開発統合ブランチ
feature/[step-name]     # 機能開発ブランチ
hotfix/[issue-name]     # 緊急修正ブランチ
release/[version]       # リリースブランチ
```

#### ブランチ運用フロー
```mermaid
gitGraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Setup"
    
    branch feature/ci-cd-setup
    checkout feature/ci-cd-setup
    commit id: "CI/CD"
    commit id: "Tests"
    
    checkout develop
    merge feature/ci-cd-setup
    
    branch feature/fastapi-foundation
    checkout feature/fastapi-foundation
    commit id: "FastAPI"
    commit id: "Middleware"
    
    checkout develop
    merge feature/fastapi-foundation
    
    branch release/v0.1.0
    checkout release/v0.1.0
    commit id: "Release prep"
    
    checkout main
    merge release/v0.1.0
    tag: "v0.1.0"
    
    checkout develop
    merge release/v0.1.0
```

### コミットメッセージ規則

#### Conventional Commits形式
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### タイプ定義
- **feat**: 新機能追加
- **fix**: バグ修正
- **docs**: ドキュメント更新
- **style**: コードスタイル変更（機能に影響なし）
- **refactor**: リファクタリング
- **perf**: パフォーマンス改善
- **test**: テスト追加・修正
- **chore**: ビルドプロセス・補助ツール変更

#### コミットメッセージ例
```bash
feat(api): implement FastAPI foundation with basic middleware

- Add FastAPI application setup
- Implement CORS and logging middleware
- Add health check endpoints
- Configure OpenAPI documentation

Closes #123
```

### マージ戦略

#### Pull Request要件
1. **必須チェック**:
   - [ ] CI/CDパイプライン成功
   - [ ] コードレビュー承認（最低1名）
   - [ ] テストカバレッジ基準達成
   - [ ] コード品質チェック通過

2. **レビュー観点**:
   - コード品質と可読性
   - テストの妥当性
   - セキュリティ考慮事項
   - パフォーマンス影響
   - ドキュメント更新

#### マージ方法
- **Squash and merge**: 機能ブランチ → develop
- **Merge commit**: develop → main
- **Fast-forward**: hotfix → main

### Git Hooks設定

#### Pre-commit Hook
**ファイル**: [`/.git/hooks/pre-commit`](.git/hooks/pre-commit)
```bash
#!/bin/sh
# Pre-commit hook for code quality checks

echo "Running pre-commit checks..."

# Run black formatting check
echo "Checking code formatting..."
black --check src tests
if [ $? -ne 0 ]; then
    echo "❌ Code formatting check failed. Run 'black src tests' to fix."
    exit 1
fi

# Run flake8 linting
echo "Running linting..."
flake8 src tests
if [ $? -ne 0 ]; then
    echo "❌ Linting check failed. Fix the issues above."
    exit 1
fi

# Run type checking
echo "Running type checking..."
mypy src
if [ $? -ne 0 ]; then
    echo "❌ Type checking failed. Fix the issues above."
    exit 1
fi

# Run tests
echo "Running tests..."
pytest tests/ -x
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Fix the failing tests."
    exit 1
fi

echo "✅ All pre-commit checks passed!"
```

#### Commit-msg Hook
**ファイル**: [`/.git/hooks/commit-msg`](.git/hooks/commit-msg)
```bash
#!/bin/sh
# Commit message validation hook

commit_regex='^(feat|fix|docs|style|refactor|perf|test|chore)(\(.+\))?: .{1,50}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "❌ Invalid commit message format!"
    echo "Format: <type>[optional scope]: <description>"
    echo "Example: feat(api): add user authentication"
    exit 1
fi

echo "✅ Commit message format is valid!"
```

## 📊 テスト実行とレポート

### テスト実行コマンド

#### 開発時テスト
```bash
# 単体テスト実行
pytest tests/unit/ -v

# 統合テスト実行
pytest tests/integration/ -v

# カバレッジ付きテスト実行
pytest --cov=src --cov-report=html --cov-report=term

# 特定モジュールのテスト
pytest tests/api/ -v

# 失敗時停止
pytest -x

# 並列実行
pytest -n auto
```

#### CI/CDテスト
```bash
# 全テスト実行（CI環境）
pytest --cov=src --cov-report=xml --cov-fail-under=85

# パフォーマンステスト
pytest tests/performance/ --benchmark-only

# セキュリティテスト
bandit -r src/
safety check
```

### テストレポート生成

#### カバレッジレポート
```bash
# HTML形式のカバレッジレポート生成
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML形式（CI用）
pytest --cov=src --cov-report=xml
```

#### テスト結果レポート
```bash
# JUnit形式のテスト結果
pytest --junitxml=test-results.xml

# HTML形式のテスト結果
pytest --html=test-report.html --self-contained-html
```

## 🚨 品質ゲートと自動化

### 品質基準

| 指標 | 最小値 | 目標値 | 測定方法 |
|------|--------|--------|----------|
| テストカバレッジ | 85% | 90% | pytest-cov |
| コード品質スコア | B | A | SonarQube |
| セキュリティスコア | 8/10 | 10/10 | Bandit + Safety |
| パフォーマンス | 500ms | 200ms | Locust |
| 可用性 | 99% | 99.9% | Uptime monitoring |

### 自動化ワークフロー

#### 継続的インテグレーション
1. **コード変更検知** → GitHub webhook
2. **品質チェック実行** → GitHub Actions
3. **テスト実行** → pytest + coverage
4. **セキュリティスキャン** → Bandit + Safety
5. **結果通知** → Slack/Email

#### 継続的デプロイメント
1. **マージ検知** → main/develop branch
2. **ビルド実行** → Docker build
3. **統合テスト** → E2E tests
4. **デプロイ実行** → Staging/Production
5. **ヘルスチェック** → API monitoring

この包括的なテスト戦略により、Phase 2の実装品質を確保し、安定したMVPを構築できます。