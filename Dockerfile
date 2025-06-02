FROM python:3.9-slim

WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# 必要なパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトファイルをコピー
COPY . /app/

# Pythonパスを設定
ENV PYTHONPATH=/app

# コンテナ起動時のデフォルトコマンド
CMD ["pytest", "-v"]