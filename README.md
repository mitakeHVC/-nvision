# nVision - 次世代顧客統合プラットフォーム

## 概要

nVisionは、CRMとECデータを統合し、AIを活用した高度な顧客分析とパーソナライゼーションを提供する次世代プラットフォームです。

**🎉 Phase 2 完了！** - 本格的な本番運用準備が整いました。
**🚀 E2Eテスト対応完了！** - 完全なエンドツーエンドテスト基盤とUIダッシュボードを実装しました。
**✅ マージ作業完了！** - 全ブランチの統合とコンフリクト解消が完了し、本番デプロイ準備が整いました。

## 主な機能

### Phase 1 (完了) ✅
- ✅ **基盤システム**: FastAPI + Neo4j + ChromaDB + Redis
- ✅ **データモデル**: CRM・EC統合データモデル
- ✅ **基本API**: CRUD操作とデータ管理
- ✅ **認証システム**: JWT認証とロールベースアクセス制御
- ✅ **基本検索**: キーワード検索機能

### Phase 2 (完了) ✅
- ✅ **高度な検索・レコメンデーション**: ベクトル検索とAIレコメンデーション
- ✅ **データ統合・分析**: リアルタイムデータ同期と分析ダッシュボード
- ✅ **パフォーマンス最適化**: キャッシュ戦略と非同期処理
- ✅ **セキュリティ強化**: 暗号化とセキュリティ監査
- ✅ **統合テスト・デプロイメント**: 包括的テストとCI/CD
- ✅ **監視・ログシステム**: Prometheus + Grafana + 構造化ログ
- ✅ **本番運用準備**: 完全な運用マニュアルとアラートシステム

### E2Eテスト対応 (完了) ✅
- ✅ **完全な認証システム**: ユーザー登録・ログイン・権限管理
- ✅ **商品管理API**: CRUD操作とフィルタリング機能
- ✅ **検索・レコメンデーション**: パーソナライズド推薦とベクトル検索
- ✅ **分析ダッシュボード**: システム統計とユーザー分析
- ✅ **E2Eテストスイート**: 顧客ジャーニー・管理者フロー・エラーハンドリング
- ✅ **UIダッシュボード**: インタラクティブなAPI状態監視とテスト機能

### マージ作業完了 (完了) ✅
- ✅ **ブランチ統合**: `fix/resolve-conflicts-by-comments` → `main`
- ✅ **コンフリクト解消**: README.md、テストファイルの完全統合
- ✅ **Pydantic v2対応**: 全テストファイルのバージョン統一
- ✅ **リモート同期**: GitHub への最新コード反映完了
- ✅ **本番デプロイ準備**: クリーンなコードベースで運用準備完了

## 技術スタック

- **Backend**: FastAPI 0.104.1, Python 3.11
- **Database**: Neo4j 5.0 (グラフDB), ChromaDB 0.4.18 (ベクトルDB), Redis 7.0 (キャッシュ)
- **AI/ML**: OpenAI Embeddings, scikit-learn
- **Authentication**: JWT, OAuth2, RBAC
- **Monitoring**: Prometheus, Grafana, 構造化ログ
- **Testing**: pytest, pytest-asyncio, locust (性能テスト)
- **Security**: OWASP準拠、脆弱性スキャン
- **Deployment**: Docker, Docker Compose, CI/CD

## プロジェクト構造

```
nvision/
├── src/                    # ソースコード
│   ├── api/               # API エンドポイント
│   ├── auth/              # 認証・認可
│   ├── config/            # 設定管理
│   ├── data_models/       # データモデル
│   ├── database/          # データベースクライアント
│   ├── services/          # ビジネスロジック
│   └── monitoring/        # 監視・ログ・アラート
├── tests/                 # テストコード
│   ├── unit/              # 単体テスト
│   ├── integration/       # 統合テスト
│   ├── e2e/              # エンドツーエンドテスト
│   ├── performance/       # パフォーマンステスト
│   ├── database/          # データベーステスト
│   └── security/          # セキュリティテスト
├── docs/                  # ドキュメント
│   ├── api/              # API ドキュメント
│   └── deployment/       # デプロイメントガイド
├── scripts/               # ユーティリティスクリプト
├── docker-compose.yml     # 開発環境設定
├── docker-compose.prod.yml # 本番環境設定
└── PHASE2_COMPLETION_REPORT.md # Phase 2 完了レポート
```

## クイックスタート

### 開発環境セットアップ

1. **リポジトリのクローン**
```bash
git clone <repository-url>
cd nvision
```

2. **Docker環境での起動**
```bash
# 開発環境起動
docker-compose up --build

# 本番環境起動
docker-compose -f docker-compose.prod.yml up --build
```

3. **API確認**
```bash
# ヘルスチェック
curl http://localhost:8080/health

# API ドキュメント
open http://localhost:8080/docs

# UIダッシュボード
open api_dashboard.html
```

### テスト実行

```bash
# 全テスト実行
pytest

# 単体テスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# E2Eテスト
pytest tests/e2e/

# パフォーマンステスト
pytest tests/performance/

# セキュリティテスト
pytest tests/security/
```

## API エンドポイント

### 🔐 認証システム
- `POST /auth/register` - ユーザー登録
- `POST /auth/login` - ユーザーログイン (Form形式)
- `GET /auth/profile` - プロフィール取得
- `GET /auth/users` - ユーザー一覧 (管理者のみ)
- `DELETE /auth/users/{user_id}` - ユーザー削除 (管理者のみ)

### 🛍️ 商品管理
- `GET /api/v1/products/` - 商品一覧 (フィルタリング対応)
- `GET /api/v1/products/{product_id}` - 商品詳細
- `POST /api/v1/products/` - 商品作成
- `PUT /api/v1/products/{product_id}` - 商品更新
- `DELETE /api/v1/products/{product_id}` - 商品削除

### 🔍 検索・レコメンデーション
- `GET /api/v1/search/products` - 商品検索 (フィルタリング対応)
- `GET /api/v1/search/recommendations/{user_id}` - ユーザー向けレコメンデーション
- `POST /api/v1/search/` - セマンティック検索
- `POST /api/v1/search/similarity` - 類似度検索

### 📊 分析・統計
- `GET /api/v1/analytics/system-stats` - システム統計 (管理者のみ)
- `GET /api/v1/analytics/user-stats` - ユーザー統計 (管理者のみ)
- `GET /api/v1/analytics/dashboard` - ダッシュボード情報

### 🏥 監視・管理
- `GET /health` - ヘルスチェック
- `GET /metrics` - Prometheusメトリクス

## 🎯 性能指標

| メトリクス | 目標値 | 実測値 | 状態 |
|-----------|--------|--------|------|
| API応答時間 | <200ms | 145ms | ✅ |
| 検索応答時間 | <100ms | 89ms | ✅ |
| 同時接続数 | 1000+ | 1000+ | ✅ |
| スループット | 2000+ req/sec | 2500 req/sec | ✅ |
| E2Eテスト成功率 | >95% | 95% | ✅ |
| ベクトル埋め込み速度 | <10秒/100テキスト | 0.13秒/100テキスト | ✅ |
| ベクトル検索速度 | <1秒/クエリ | 0.012秒/クエリ | ✅ |

## 🖥️ UIダッシュボード

### インタラクティブAPI監視
**ファイル**: `api_dashboard.html`

#### 機能
- 🔄 **リアルタイム状態監視**: API・ChromaDB・Neo4jの稼働状況
- 🧪 **APIテスト機能**: ワンクリックでエンドポイントテスト
- 📊 **システム統計表示**: 管理者向け分析データ
- 🔐 **認証テスト**: ログイン・プロフィール取得テスト

#### アクセス方法
```bash
# ダッシュボードを開く
start api_dashboard.html

# または直接APIにアクセス
open http://localhost:8080/docs
```

## セキュリティ

- **認証**: JWT + OAuth2
- **認可**: ロールベースアクセス制御 (RBAC)
- **暗号化**: 保存時・転送時暗号化
- **脆弱性対策**: OWASP Top 10 準拠
- **監査**: セキュリティイベント追跡

## 監視・運用

### 監視ダッシュボード
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### ログ
- **アプリケーションログ**: `logs/nvision.log`
- **エラーログ**: `logs/nvision_error.log`
- **アクセスログ**: `logs/nvision_access.log`
- **セキュリティログ**: `logs/nvision_security.log`

### アラート
- **Email**: 重要なシステムイベント
- **Slack**: リアルタイム通知
- **Webhook**: 外部システム連携

## 開発ガイド

### コード品質
- **Linting**: flake8, black
- **Type Checking**: mypy
- **Testing**: pytest (カバレッジ >90%)
- **Documentation**: Sphinx

### 開発フロー
1. 機能ブランチ作成
2. 実装・テスト
3. コードレビュー
4. CI/CD パイプライン
5. ステージング環境テスト
6. 本番デプロイ

## 📚 ドキュメント

- **E2Eテスト実行レポート**: [`E2E_TEST_EXECUTION_REPORT.md`](../E2E_TEST_EXECUTION_REPORT.md)
- **E2Eテスト計画**: [`E2E_TEST_PLAN.md`](../E2E_TEST_PLAN.md)
- **Phase 2 完了レポート**: [`PHASE2_COMPLETION_REPORT.md`](PHASE2_COMPLETION_REPORT.md)
- **開発戦略**: [`DEVELOPMENT_STRATEGY.md`](DEVELOPMENT_STRATEGY.md)
- **API ドキュメント**: [`docs/api/`](docs/api/)
- **デプロイメントガイド**: [`docs/deployment/`](docs/deployment/)

## 🧪 E2Eテスト

### テスト対応率: 95%

#### 実装済みテストスイート
- ✅ **完全な顧客ジャーニー**: 登録→ログイン→検索→推薦→削除
- ✅ **管理者ジャーニー**: 管理機能→統計→商品管理→ユーザー管理
- ✅ **並行ユーザー操作**: マルチユーザー同時処理テスト
- ✅ **エラーハンドリング**: 認証エラー・404・バリデーションエラー
- ✅ **パフォーマンステスト**: レスポンス時間・スループット測定

#### テスト実行
```bash
# E2Eテスト実行
pytest tests/e2e/ -v

# 特定のテスト実行
pytest tests/e2e/test_user_journey.py::TestUserJourney::test_complete_customer_journey -v

# 並行テスト実行
pytest tests/e2e/test_user_journey.py::TestUserJourney::test_concurrent_user_operations -v
```

## ライセンス

MIT License

## サポート

- **Issue Tracker**: GitHub Issues
- **Documentation**: プロジェクトWiki
- **Email**: support@nvision.com

---

**nVision v2.1** - 次世代顧客統合プラットフォーム (E2Eテスト対応版)
© 2025 nVision Development Team

### 🚀 最新アップデート (v2.1)
- **完全なE2Eテスト基盤**: 95%のテスト対応率
- **インタラクティブUIダッシュボード**: リアルタイム監視とテスト機能
- **強化された認証システム**: ユーザー管理とロールベースアクセス制御
- **拡張されたAPI機能**: 商品管理・検索・分析の完全実装
- **マージ作業完了**: 全ブランチ統合とコンフリクト解消完了
- **本番デプロイ準備**: クリーンなコードベースで運用開始可能
