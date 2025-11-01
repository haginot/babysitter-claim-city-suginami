FROM python:3.11-slim

WORKDIR /app

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存パッケージをインストール
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY backend/app.py .

# ポート5000を公開
EXPOSE 5000

# アプリケーションを起動
CMD ["python", "app.py"]
