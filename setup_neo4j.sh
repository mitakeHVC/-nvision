#!/bin/bash

# Neo4jコンテナが起動しているか確認
if ! docker-compose ps | grep -q "neo4j.*Up"; then
    echo "Neo4jコンテナを起動しています..."
    docker-compose up -d neo4j
    sleep 5  # Neo4jの起動を待つ
fi

# スキーマファイルをNeo4jのインポートディレクトリにコピー
echo "スキーマファイルをNeo4jコンテナにコピーしています..."
docker cp src/neo4j_setup/ec_schema.cypher $(docker-compose ps -q neo4j):/var/lib/neo4j/import/

# スキーマを適用
echo "Neo4jにスキーマを適用しています..."
docker-compose exec neo4j cypher-shell -u neo4j -p password -f /var/lib/neo4j/import/ec_schema.cypher

echo "Neo4jスキーマのセットアップが完了しました"