# AI Brain

个人智能知识库与 AI 助理平台 —— 一个具备「私有 RAG + Agent Tool Calling + 流式对话」完整 AI 全栈能力的 Web 产品。

> 当前处于 **Phase 1：项目骨架与基础设施** 阶段（尚未实现 RAG / Agent / 业务功能）。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Axios + Element Plus |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic + Pydantic v2 |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存/限流 | Redis 7 |
| AI | DeepSeek（LLM）、SiliconFlow BGE-M3（Embedding） |
| 部署 | Docker Compose + Nginx |

## 目录结构

```
ai-brain/
├── backend/            # FastAPI 模块化单体
│   ├── app/
│   │   ├── api/        # API Layer（路由）
│   │   ├── core/       # 配置
│   │   ├── models/     # SQLAlchemy ORM 模型
│   │   ├── schemas/    # Pydantic 模型
│   │   ├── repositories/  # 数据访问层
│   │   ├── services/   # 业务层
│   │   ├── ai/         # AI Provider 抽象
│   │   ├── rag/        # RAG 层
│   │   ├── agent/      # Agent 层
│   │   ├── document/   # 文档处理层
│   │   └── infrastructure/  # DB / Redis
│   ├── alembic/        # 数据库迁移
│   └── tests/
├── frontend/           # Vue 3 SPA
├── docker-compose.yml
├── .env.example
└── README.md
```

## 环境要求

- Docker & Docker Compose（推荐）
- 或手动安装：Python 3.12+、Node 20+、PostgreSQL 16 + pgvector、Redis 7

## 快速开始（Docker，推荐）

```bash
# 1. 准备环境变量（可选，不填则使用默认开发配置）
cp .env.example .env

# 2. 启动全部服务（postgres + redis + backend + frontend）
docker compose up -d --build

# 3. 验证
curl http://localhost:8000/health
# 前端：http://localhost:80
```

后端容器启动时会自动执行 `alembic upgrade head` 创建全部 9 张表并启用 pgvector。

## 本地开发（手动，不使用 Docker）

### 1. 启动基础设施

```bash
# 仅启动 postgres + redis
docker compose up -d postgres redis
```

### 2. 后端

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# 配置环境变量
cp ../.env.example .env   # 编辑 .env，DATABASE_URL/REDIS_URL 指向 localhost

# 执行数据库迁移
alembic upgrade head

# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## 数据库迁移

迁移文件位于 `backend/alembic/versions/`，顺序如下（依赖 pgvector 扩展在 document_chunks 之前）：

| 迁移 | 内容 |
|---|---|
| 0001 | create_users |
| 0002 | create_conversations_messages |
| 0003 | create_knowledge_bases_documents |
| 0004 | enable_pgvector |
| 0005 | create_document_chunks |
| 0006 | create_tasks |
| 0007 | create_ai_usage_logs |
| 0008 | create_agent_tool_calls |

```bash
cd backend
alembic upgrade head       # 升级到最新
alembic downgrade -1       # 回退一个版本
alembic current            # 查看当前版本
```

## 健康检查

`GET /health` 返回：

```json
{ "status": "ok", "database": "ok", "redis": "ok" }
```

- `status=ok` 且 HTTP 200：全部正常
- `status=degraded` 且 HTTP 503：数据库或 Redis 异常

## 环境变量

见 `.env.example`。真实 API Key 只放后端环境变量，**禁止提交到 Git**。

## 测试

```bash
cd backend
pytest
```

## 生产部署（公网上线完整指南）

### 1. 云服务器要求

| 项 | 建议 |
|---|---|
| 配置 | 2 核 4G 内存起步（PostgreSQL + FastAPI + Nginx + Redis 同机） |
| 系统 | Ubuntu 22.04 LTS |
| 磁盘 | 40GB 起（上传文档与向量数据） |
| 网络 | 开放 80 / 443 端口（**不要**开放 5432 / 6379 / 8000） |

### 2. 安装 Docker 与 Compose

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 重新登录后生效
docker --version && docker compose version
```

### 3. 上传项目

```bash
# 本机打包（.env 会被 .gitignore 排除，也可用 git clone 替代）
scp -r "D:/ai brain" user@your-server:/opt/aibrain
# 或服务器上 git clone 你的仓库
cd /opt/aibrain
```

### 4. 配置 .env（必填 4 项）

```bash
cp .env.example .env
vi .env
```

```ini
JWT_SECRET_KEY=openssl_rand_hex_32_的输出          # 生成：openssl rand -hex 32
POSTGRES_PASSWORD=改一个强密码                      # 不要用默认 aibrain
DEEPSEEK_API_KEY=sk-...                            # DeepSeek 平台申请
EMBEDDING_API_KEY=sk-...                           # SiliconFlow 平台申请（BGE-M3）
```

### 5. 启动（生产模式：端口最小化暴露）

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps          # 4 容器 healthy
curl http://127.0.0.1:8080 # 前端应响应
curl http://127.0.0.1:8000/health   # {"status":"ok",...}
```

### 6. 域名 DNS

在域名服务商处添加 A 记录：`your-domain.com → 服务器公网 IP`，等待解析生效。

### 7. 宿主机 Nginx（反向代理入口）

```bash
sudo apt install -y nginx
sudo vi /etc/nginx/sites-available/aibrain
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE 流式（已由容器内 Nginx 关闭缓冲，此处同样保持）
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/aibrain /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 8. HTTPS / Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com   # 自动签发 + 自动续期
```

### 9. 数据库备份

```bash
# 每日定时备份（crontab -e 加入）
0 3 * * * docker exec aibrain-postgres pg_dump -U aibrain aibrain > /opt/backups/aibrain_$(date +\%F).sql
# 恢复：cat backup.sql | docker exec -i aibrain-postgres psql -U aibrain -d aibrain
```

### 10. 日志查看

```bash
docker compose logs -f backend     # 后端日志（含请求日志/迁移/异常）
docker compose logs -f postgres    # 数据库日志
docker logs aibrain-frontend       # Nginx 访问/错误日志
```

### 11. 更新项目的方法

```bash
cd /opt/aibrain
git pull                          # 拉取新代码
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# 数据库结构变更会自动通过 alembic upgrade head 执行
```

### 12. 常见故障排查

| 现象 | 排查 |
|---|---|
| 前端 502 | `docker compose ps` 看 backend 是否 Up；`docker compose logs backend` 看报错 |
| /health degraded | 检查 postgres/redis 容器与网络：`docker compose ps` |
| 上传 413 | 宿主机与容器内 Nginx 的 `client_max_body_size` 都需 ≥20m |
| 聊天报 AI 服务失败 | 检查 `.env` 的 `DEEPSEEK_API_KEY` 是否有效、余额是否充足 |
| 上传解析失败(failed) | `docker compose logs backend` 看 `error_message`；扫描版 PDF 不支持 |
| 页面 404（刷新子路由） | 容器 Nginx 已配置 `try_files /index.html`；宿主机 Nginx 也需按第 7 步配置 |

## 当前阶段说明

第一版（v1.0）功能全部完成：用户系统、AI Chat（SSE/多轮）、知识库（上传/解析/Embedding/pgvector）、RAG 问答（引用来源）、文档总结、Agent Tool Calling（任务工具）、用量统计。
