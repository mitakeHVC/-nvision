#!/bin/bash

# 使用方法を表示する関数
show_usage() {
    echo "使用方法: $0 [オプション]"
    echo "オプション:"
    echo "  -h, --help       このヘルプメッセージを表示"
    echo "  -t, --test       特定のテストを実行 (例: -t test_ec_models)"
    echo "  -s, --setup      Neo4jスキーマをセットアップ"
    echo "  -b, --build      コンテナを再ビルド"
    echo "例:"
    echo "  $0               全てのテストを実行"
    echo "  $0 -t ec_models  ECモデルのテストのみ実行"
    echo "  $0 -s -b         Neo4jスキーマをセットアップし、コンテナを再ビルド"
}

# デフォルト値
TEST_PATH="tests"
SETUP_NEO4J=false
REBUILD=false

# 引数の解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -t|--test)
            if [[ -n $2 ]]; then
                TEST_PATH="tests/data_models/test_$2.py"
                shift
            else
                echo "エラー: --test オプションには引数が必要です"
                exit 1
            fi
            ;;
        -s|--setup)
            SETUP_NEO4J=true
            ;;
        -b|--build)
            REBUILD=true
            ;;
        *)
            echo "不明なオプション: $1"
            show_usage
            exit 1
            ;;
    esac
    shift
done

# コンテナの再ビルドが必要な場合
if [ "$REBUILD" = true ]; then
    echo "コンテナを再ビルドしています..."
    docker-compose build
fi

# Neo4jスキーマのセットアップが必要な場合
if [ "$SETUP_NEO4J" = true ]; then
    echo "Neo4jスキーマをセットアップしています..."
    docker-compose up -d neo4j
    sleep 5  # Neo4jの起動を待つ
    
    # Neo4jにスキーマを適用
    docker-compose exec neo4j cypher-shell -u neo4j -p password -f /var/lib/neo4j/import/ec_schema.cypher
    
    echo "Neo4jスキーマのセットアップが完了しました"
fi

# テストの実行
echo "テストを実行しています: $TEST_PATH"
docker-compose run --rm app pytest -v $TEST_PATH

# 終了メッセージ
echo "テスト実行が完了しました"