FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
# 国内 PyPI 镜像 + 超时重试（服务器网络优化；依赖版本不变）
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --timeout 60 \
    --retries 5 \
    -r requirements.txt

COPY . .

EXPOSE 8000

# 生产启动：先执行数据库迁移，再启动服务（--proxy-headers 信任 Nginx 反代头）
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
