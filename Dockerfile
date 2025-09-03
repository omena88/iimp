# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application
COPY backend/ /app/backend/

# Copy frontend files
COPY frontend/ /var/www/html/

# Create nginx configuration
RUN echo 'server { \
    listen 80; \
    server_name _; \
    \
    # Serve frontend files \
    location / { \
        root /var/www/html; \
        index index.html; \
        try_files $uri $uri/ =404; \
    } \
    \
    # Proxy API requests to FastAPI backend \
    location /api/ { \
        proxy_pass http://127.0.0.1:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
}' > /etc/nginx/sites-available/default

# Create supervisor configuration
RUN echo '[supervisord] \
nodaemon=true \
\
[program:nginx] \
command=nginx -g "daemon off;" \
autostart=true \
autorestart=true \
stderr_logfile=/var/log/nginx.err.log \
stdout_logfile=/var/log/nginx.out.log \
\
[program:fastapi] \
command=python -m uvicorn main:app --host 0.0.0.0 --port 8000 \
directory=/app/backend \
autostart=true \
autorestart=true \
stderr_logfile=/var/log/fastapi.err.log \
stdout_logfile=/var/log/fastapi.out.log' > /etc/supervisor/conf.d/supervisord.conf

# Expose port 80
EXPOSE 80

# Start supervisor
CMD ["/usr/bin/supervisord"]