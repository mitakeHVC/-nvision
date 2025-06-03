# Contributing to nvision

nvisionプロジェクトへの貢献をお考えいただき、ありがとうございます！このドキュメントでは、プロジェクトに貢献するためのガイドラインと手順を説明します。

## 📋 目次

- [開発環境のセットアップ](#開発環境のセットアップ)
- [Git ワークフロー](#git-ワークフロー)
- [コーディング規約](#コーディング規約)
- [テスト戦略](#テスト戦略)
- [コードレビュープロセス](#コードレビュープロセス)
- [コミットメッセージ規約](#コミットメッセージ規約)
- [プルリクエストガイドライン](#プルリクエストガイドライン)
- [問題報告](#問題報告)

## 🚀 開発環境のセットアップ

### 前提条件

- Python 3.9以上
- Docker & Docker Compose
- Git
- Make（推奨）

### セットアップ手順

1. **リポジトリのクローン**
   ```bash
   git clone https://github.com/your-org/nvision.git
   cd nvision
   ```

2. **開発環境の構築**
   ```bash
   # Makeを使用する場合
   make setup-dev
   
   # 手動でセットアップする場合
   pip install -e ".[dev,test]"
   pre-commit install
   cp .env.example .env
   ```

3. **データベースサービスの起動**
   ```bash
   make db-start
   # または
   docker-compose up -d neo4j chroma
   ```

4. **動作確認**
   ```bash
   make test
   # または
   pytest
   ```

## 🔄 Git ワークフロー

### ブランチ戦略

プロジェクトでは **Git Flow** を採用しています：

- `main`: 本番環境用の安定版
- `develop`: 開発統合ブランチ
- `feature/*`: 新機能開発用
- `bugfix/*`: バグ修正用
- `hotfix/*`: 緊急修正用
- `release/*`: リリース準備用

### 開発フロー

1. **Issue の作成**
   - 新機能や修正内容について Issue を作成
   - 適切なラベルとマイルストーンを設定

2. **ブランチの作成**
   ```bash
   # 新機能の場合
   git checkout develop
   git pull origin develop
   git checkout -b feature/issue-123-add-new-feature
   
   # バグ修正の場合
   git checkout -b bugfix/issue-456-fix-bug-description
   ```

3. **開発とコミット**
   ```bash
   # 開発作業
   # ...
   
   # ステージングとコミット
   git add .
   git commit -m "feat: add new customer search functionality"
   ```

4. **プッシュとプルリクエスト**
   ```bash
   git push origin feature/issue-123-add-new-feature
   # GitHub でプルリクエストを作成
   ```

## 📝 コーディング規約

### Python コーディングスタイル

- **PEP 8** に準拠
- **Black** でコードフォーマット（行長: 88文字）
- **isort** でインポート整理
- **Type hints** を必須使用

### コード品質ツール

```bash
# フォーマット
make format

# リンティング
make lint

# 型チェック
make type-check

# セキュリティチェック
make security-check

# 全品質チェック
make quality-check
```

### ディレクトリ構造

```
src/
├── api/                 # FastAPI アプリケーション
│   ├── main.py         # アプリケーションエントリーポイント
│   ├── dependencies.py # 依存性注入
│   ├── middleware.py   # ミドルウェア
│   └── routers/        # API ルーター
├── data_models/        # データモデル
├── database/           # データベース接続
├── repositories/       # データアクセス層
├── services/          # ビジネスロジック層
└── config/            # 設定管理

tests/
├── unit/              # ユニットテスト
├── integration/       # 統合テスト
└── e2e/              # E2Eテスト
```

### 命名規約

- **関数・変数**: `snake_case`
- **クラス**: `PascalCase`
- **定数**: `UPPER_SNAKE_CASE`
- **ファイル・モジュール**: `snake_case`
- **プライベート**: `_leading_underscore`

## 🧪 テスト戦略

### テストの種類

1. **ユニットテスト** (`tests/unit/`)
   - 個別の関数・クラスのテスト
   - モックを使用した独立テスト
   - 高速実行が可能

2. **統合テスト** (`tests/integration/`)
   - 複数コンポーネント間の連携テスト
   - データベース接続を含むテスト
   - 実際のサービス間通信テスト

3. **E2Eテスト** (`tests/e2e/`)
   - エンドツーエンドのワークフローテスト
   - API エンドポイントの完全テスト
   - 実際のユーザーシナリオテスト

### テスト実行

```bash
# 全テスト実行
make test

# 種類別テスト実行
make test-unit
make test-integration
make test-e2e

# カバレッジレポート生成
make coverage-report
```

### テスト作成ガイドライン

- **AAA パターン** (Arrange, Act, Assert) を使用
- **テスト名** は動作を明確に表現
- **モック** は適切に使用し、外部依存を排除
- **テストデータ** は fixtures で管理
- **カバレッジ** は 85% 以上を維持

### テスト例

```python
def test_create_customer_success():
    """顧客作成が正常に動作することをテスト"""
    # Arrange
    customer_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com"
    }
    
    # Act
    result = customer_service.create_customer(customer_data)
    
    # Assert
    assert result.customer_id is not None
    assert result.email == "test@example.com"
```

## 👥 コードレビュープロセス

### レビュー要件

- **必須レビュアー**: 最低1名のコアメンバー
- **自動チェック**: CI/CD パイプラインが全て通過
- **コンフリクト解決**: マージ前に解決必須

### レビューポイント

1. **機能性**
   - 要件を満たしているか
   - エッジケースが考慮されているか
   - エラーハンドリングが適切か

2. **コード品質**
   - 可読性が高いか
   - 適切な抽象化がされているか
   - パフォーマンスに問題がないか

3. **テスト**
   - 適切なテストが書かれているか
   - カバレッジが十分か
   - テストが意味のあるものか

4. **セキュリティ**
   - セキュリティ脆弱性がないか
   - 入力値検証が適切か
   - 認証・認可が正しく実装されているか

### レビューコメント例

```markdown
# 良いコメント例
- "この関数は複雑すぎるので、小さな関数に分割することを提案します"
- "エラーケースのテストが不足しているようです"
- "パフォーマンスの観点から、この処理をキャッシュすることを検討してください"

# 避けるべきコメント例
- "これは間違っています"（理由が不明確）
- "私ならこうします"（代替案が不明確）
```

## 📝 コミットメッセージ規約

### Conventional Commits

プロジェクトでは **Conventional Commits** 規約を採用しています。

### フォーマット

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Type の種類

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードスタイル変更（機能に影響なし）
- `refactor`: リファクタリング
- `perf`: パフォーマンス改善
- `test`: テスト追加・修正
- `chore`: ビルドプロセス・補助ツール変更
- `ci`: CI/CD 設定変更

### 例

```bash
# 新機能追加
git commit -m "feat(api): add customer search endpoint"

# バグ修正
git commit -m "fix(database): resolve connection timeout issue"

# ドキュメント更新
git commit -m "docs: update API documentation"

# 破壊的変更
git commit -m "feat!: change API response format

BREAKING CHANGE: API response format has been changed from array to object"
```

## 📋 プルリクエストガイドライン

### PR テンプレート

プルリクエスト作成時は以下の情報を含めてください：

```markdown
## 概要
このPRの目的と変更内容を簡潔に説明

## 変更内容
- [ ] 新機能追加
- [ ] バグ修正
- [ ] リファクタリング
- [ ] ドキュメント更新
- [ ] テスト追加

## 関連Issue
Closes #123

## テスト
- [ ] ユニットテストを追加/更新
- [ ] 統合テストを追加/更新
- [ ] 手動テストを実施

## チェックリスト
- [ ] コードレビューを受けた
- [ ] CI/CDが通過している
- [ ] ドキュメントを更新した
- [ ] 破壊的変更がある場合、マイグレーション手順を記載

## スクリーンショット（該当する場合）
```

### PR サイズガイドライン

- **小さなPR** を推奨（変更行数: 200行以下）
- **単一責任** を持つPR
- **レビューしやすい** サイズに分割

## 🐛 問題報告

### バグレポート

Issue テンプレートを使用してバグを報告してください：

```markdown
## バグの説明
バグの内容を明確に説明

## 再現手順
1. '...' に移動
2. '...' をクリック
3. '...' まで下にスクロール
4. エラーを確認

## 期待される動作
何が起こるべきかを説明

## 実際の動作
実際に何が起こったかを説明

## 環境
- OS: [例: macOS 12.0]
- Python: [例: 3.9.7]
- ブラウザ: [例: Chrome 95.0]

## 追加情報
スクリーンショット、ログ、その他の関連情報
```

### 機能リクエスト

```markdown
## 機能の説明
提案する機能の詳細な説明

## 動機
なぜこの機能が必要なのか

## 詳細設計
可能であれば、実装方法の提案

## 代替案
検討した他の解決策
```

## 🎯 開発のベストプラクティス

### 1. 小さく頻繁なコミット
- 論理的な単位でコミット
- 1つのコミットで1つの変更
- 意味のあるコミットメッセージ

### 2. テスト駆動開発（TDD）
- テストを先に書く
- Red → Green → Refactor サイクル
- 高いテストカバレッジを維持

### 3. 継続的インテグレーション
- 頻繁にmainブランチと同期
- CI/CDパイプラインを活用
- 自動化されたテストを信頼

### 4. ドキュメント重視
- コードと同時にドキュメント更新
- API仕様書の維持
- README の最新化

## 🤝 コミュニティ

### コミュニケーション

- **GitHub Issues**: バグ報告・機能リクエスト
- **GitHub Discussions**: 一般的な議論
- **Pull Requests**: コードレビュー

### 行動規範

- 建設的で敬意のあるコミュニケーション
- 多様性と包括性の尊重
- 学習と成長の機会として捉える

## 📚 参考資料

- [Python PEP 8](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [pytest Documentation](https://docs.pytest.org/)

---

質問や不明な点がありましたら、Issue を作成するか、プロジェクトメンテナーにお気軽にお声かけください。

貢献をお待ちしています！ 🚀