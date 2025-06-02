# Data Schema and Transformation Implementation

このプロジェクトは、`data_schema_and_transformation_proposal.md`ドキュメントに概説されているデータスキーマ、関係、変換ロジックを実装することを目的としています。

## プロジェクト概要

このプロジェクトでは、E-commerce（EC）システム、CRMシステム、および共有/サポートシステムのデータモデルを実装し、Neo4jグラフデータベースとChromaDBベクトルデータベースを使用してデータを管理・分析します。

## プロジェクト構造

```
.
├── data_schema_and_transformation_proposal.md  # データスキーマと変換の提案書
├── src/
│   ├── data_models/                           # Pydanticデータモデル
│   │   ├── ec_models.py                       # ECシステムのモデル
│   │   ├── crm_models.py                      # CRMシステムのモデル
│   │   └── shared_models.py                   # 共有システムのモデル
│   └── neo4j_setup/                           # Neo4jスキーマ設定
│       └── ec_schema.cypher                   # ECシステムのNeo4jスキーマ
├── tests/                                     # テストディレクトリ
│   └── data_models/                           # データモデルのテスト
│       ├── test_ec_models.py                  # ECモデルのテスト
│       ├── test_crm_models.py                 # CRMモデルのテスト
│       └── test_shared_models.py              # 共有モデルのテスト
├── Dockerfile                                 # Dockerコンテナ定義
├── docker-compose.yml                         # Docker Compose設定
├── requirements.txt                           # Pythonパッケージ依存関係
├── run_tests.sh                               # テスト実行スクリプト
└── setup_neo4j.sh                             # Neo4jセットアップスクリプト
```

## 現在の状態

- **E-commerce (EC) データモデル:** ECシステムのエンティティ（顧客、製品、カテゴリ、注文、注文アイテム、サプライヤ、顧客レビュー）のPython Pydanticモデルが`src/data_models/ec_models.py`に実装されています。
- **CRM データモデル:** CRMシステムのエンティティ（連絡先、会社、インタラクション、商談、ユーザー）のPython Pydanticモデルが`src/data_models/crm_models.py`に実装されています。
- **共有/サポートデータモデル:** 共有エンティティ（チャットセッション、チャットメッセージ）のPython Pydanticモデルが`src/data_models/shared_models.py`に実装されています。
- **Neo4jスキーマ:** E-commerceエンティティの初期Neo4jスキーマが`src/neo4j_setup/ec_schema.cypher`に定義されています。
- **Dockerサポート:** 開発とテスト用のDockerおよびdocker-compose設定が実装されています。

## 使用方法

### 環境構築

#### Dockerを使用する場合

1. Dockerとdocker-composeをインストールします
2. プロジェクトのルートディレクトリで以下のコマンドを実行します：

```bash
# Dockerイメージをビルド
docker-compose build

# Neo4jコンテナを起動してスキーマをセットアップ
./setup_neo4j.sh
```

#### ローカル環境を使用する場合

1. Python 3.9以上をインストールします
2. 必要なパッケージをインストールします：

```bash
pip install -r requirements.txt
```

3. PYTHONPATHを設定します：

```bash
# Linuxまたは macOS
export PYTHONPATH=$PWD

# Windows
set PYTHONPATH=%CD%
```

### テストの実行

#### Dockerを使用する場合

すべてのテストを実行：

```bash
./run_tests.sh
```

特定のテストのみを実行：

```bash
./run_tests.sh -t ec_models    # ECモデルのテストのみ実行
./run_tests.sh -t crm_models   # CRMモデルのテストのみ実行
./run_tests.sh -t shared_models # 共有モデルのテストのみ実行
```

コンテナを再ビルドしてテストを実行：

```bash
./run_tests.sh -b
```

#### ローカル環境を使用する場合

すべてのテストを実行：

```bash
pytest -v
```

特定のテストのみを実行：

```bash
pytest -v tests/data_models/test_ec_models.py
pytest -v tests/data_models/test_crm_models.py
pytest -v tests/data_models/test_shared_models.py
```

### Neo4jスキーマのセットアップ

#### Dockerを使用する場合

```bash
./setup_neo4j.sh
```

#### ローカル環境を使用する場合

1. Neo4jをインストールして起動します
2. 以下のコマンドを実行してスキーマをセットアップします：

```bash
cat src/neo4j_setup/ec_schema.cypher | cypher-shell -u neo4j -p password
```

### データモデルの使用例

```python
from src.data_models.ec_models import Customer, Product, Order
from datetime import datetime

# 顧客の作成
customer = Customer(
    CustomerID=1,
    FirstName="山田",
    LastName="太郎",
    Email="yamada@example.com",
    RegistrationDate=datetime.now()
)

# 製品の作成
product = Product(
    ProductID=101,
    ProductName="ノートパソコン",
    Description="高性能ノートパソコン",
    Price=120000.0,
    StockQuantity=10
)

# 注文の作成
order = Order(
    OrderID=1001,
    CustomerID=customer.CustomerID,
    OrderDate=datetime.now(),
    OrderStatus="処理中",
    TotalAmount=120000.0
)

# データの検証
print(customer.json(indent=2))
print(product.json(indent=2))
print(order.json(indent=2))
```

## 次のステップ

プロジェクトは以下の作業を進める予定です：
- Neo4jデータ取り込みロジックの実装
- ChromaDBベクトル埋め込み戦略とデータ取り込みロジックの実装
- データアクセス用APIエンドポイントの開発
- データ変換パイプラインの構築
- フロントエンドインターフェースの開発

## 貢献方法

1. このリポジトリをフォークします
2. 新しいブランチを作成します (`git checkout -b feature/amazing-feature`)
3. 変更をコミットします (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュします (`git push origin feature/amazing-feature`)
5. プルリクエストを作成します

## ライセンス

このプロジェクトは社内利用のみを目的としています。
