# Nginx + Flask統合イメージ（Supervisor使用）
FROM nginx:alpine

# Pythonとsupervisorをインストール
RUN apk add --no-cache python3 py3-pip supervisor

# Pythonの依存関係をインストール
COPY backend/requirements.txt /app/backend/
RUN pip3 install --no-cache-dir --break-system-packages -r /app/backend/requirements.txt

# バックエンドのコードをコピー
COPY backend/app.py /app/backend/

# フロントエンドのファイルをコピー
COPY frontend /usr/share/nginx/html/frontend

# Nginxの設定をコピー（Render用）
COPY nginx.render.conf /etc/nginx/conf.d/default.conf

# Supervisorの設定を作成
RUN echo '[supervisord]' > /etc/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisord.conf && \
    echo 'user=root' >> /etc/supervisord.conf && \
    echo '' >> /etc/supervisord.conf && \
    echo '[program:flask]' >> /etc/supervisord.conf && \
    echo 'command=python3 -m gunicorn -w 4 -b 0.0.0.0:5000 app:app' >> /etc/supervisord.conf && \
    echo 'directory=/app/backend' >> /etc/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf && \
    echo 'environment=PORT=5000' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo '' >> /etc/supervisord.conf && \
    echo '[program:nginx]' >> /etc/supervisord.conf && \
    echo 'command=nginx -g "daemon off;"' >> /etc/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf

# Nginxを80ポートで起動
EXPOSE 80

# Supervisorで両方のプロセスを起動
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]