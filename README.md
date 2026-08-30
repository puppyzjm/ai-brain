# AI Brain

个人智能知识库与 AI 助理平台 —— 一个具备「私有 RAG + Agent Tool Calling + 流式对话」完整 AI 全栈能力的 Web 产品。

[![CI](https://github.com/puppyzjm/ai-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/puppyzjm/ai-brain/actions/workflows/ci.yml)

## 核心能力

| 能力 | 说明 |
|---|---|
| 📚 知识库 + RAG 问答 | 上传 PDF/TXT/Markdown → 解析 → BGE-M3 向量化 → pgvector 检索 → 流式回答 + 引用来源（检索不足不编造） |
| 🔀 混合检索 | 向量语义检索 + BM25 关键词检索（jieba 分词）→ RRF 融合，中文精确命中更好 |
| 📄 扫描版 PDF OCR | 自动识别无文字层页面 → DeepSeek-OCR 提取文字并入索引（文字页零成本直通） |
| 🖼 多模态图片问答 | 聊天框粘贴截图 → Qwen3-VL 视觉模型看图回答（≤3 张、压缩传输、安全校验） |
| 💬 AI 流式对话 | 多轮对话、SSE 流式、Markdown/代码高亮、停止生成 |
| 🤖 Agent 任务管理 | DeepSeek Function Calling：AI 自主创建/查询/修改/删除任务 + 检索知识库 |
| 🔐 安全认证 | JWT 短期访问令牌 + Refresh Token 轮换防重放、注销撤销；图片/文档魔数校验、用户数据全隔离 |
| 📝 文档总结 | 一键生成结构化摘要（核心主题/要点/建议） |
| 📊 用量统计 | 调用次数、Token、成功率、近 7 天趋势 |

## 文档

- [架构设计](docs/architecture.md)（架构图 / 技术选型 / 分层铁律）
- [API 文档](docs/api.md)（全部 REST + SSE 接口）
- [数据库设计](docs/database.md)（10 张表 + ER 图 + pgvector）

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Axios + Element Plus |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic + Pydantic v2 |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存/限流 | Redis 7 |
| AI | DeepSeek（LLM）、SiliconFlow BGE-M3（Embedding）、DeepSeek-OCR（扫描件文字提取）、Qwen3-VL（视觉问答） |
| 检索 | pgvector 向量 + BM25（jieba + rank-bm25）+ RRF 融合 |
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
# 前端：http://localhost:8080
```

后端容器启动时会自动执行 `alembic upgrade head` 创建全部 10 张表并启用 pgvector。

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
| 0009 | create_refresh_tokens |
| 0010 | messages 增加 images（多模态） |
| 0011 | ai_usage_logs 类型扩展 vision |

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
pytest   # 45 个用例：鉴权/越权/CRUD/RAG/缓存失效/图片上传校验 + 真实 AI 调用集成用例
```

> CI（GitHub Actions）无真实 API Key，会跳过需要真实 LLM / 视觉模型调用的用例（本地 .env 配置 Key 后全量执行）。

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

### 4. 配置 .env（必填项）

```bash
cp .env.example .env
vi .env
```

```ini
JWT_SECRET_KEY=openssl_rand_hex_32_的输出          # 生成：openssl rand -hex 32（≥32 字节）
POSTGRES_PASSWORD=改一个强密码                      # 不要用默认 aibrain
DEEPSEEK_API_KEY=sk-...                            # DeepSeek 平台申请（对话 LLM）
EMBEDDING_API_KEY=sk-...                           # SiliconFlow 平台申请（BGE-M3 / OCR / 视觉模型共用）
```

可选：`OCR_MODEL`、`VISION_MODEL` 默认即 DeepSeek-OCR 与 Qwen3-VL，一般无需修改。

### 5. 启动（单文件编排，端口全部绑定 127.0.0.1）

```bash
docker compose up -d --build
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
cd /opt/ai-brain
git pull                          # 拉取新代码
docker compose up -d --build
# 数据库结构变更会自动通过 alembic upgrade head 执行
```

### 12. 常见故障排查

| 现象 | 排查 |
|---|---|
| 前端 502 | `docker compose ps` 看 backend 是否 Up；`docker compose logs backend` 看报错 |
| /health degraded | 检查 postgres/redis 容器与网络：`docker compose ps` |
| 上传 413 | 宿主机与容器内 Nginx 的 `client_max_body_size` 都需 ≥20m |
| 聊天报 AI 服务失败 | 检查 `.env` 的 `DEEPSEEK_API_KEY` 是否有效、余额是否充足 |
| 图片上传被拒(4004) | 仅支持 PNG/JPG/WebP 且 ≤5MB；服务端按文件头魔数校验，伪装扩展名会被拒绝 |
| 图片问答报错 | 检查 `EMBEDDING_API_KEY`（视觉模型复用 SiliconFlow Key）与 `VISION_MODEL` 配置 |
| 上传解析失败(failed) | `docker compose logs backend` 看 `error_message`；扫描版 PDF 会自动走 OCR，OCR 失败时在此显示原因 |
| 页面 404（刷新子路由） | 容器 Nginx 已配置 `try_files /index.html`；宿主机 Nginx 也需按第 7 步配置 |

## 当前阶段说明

v1.x 功能全部完成并上线：用户系统（JWT + Refresh Token 轮换防重放）、AI Chat（SSE/多轮）、知识库（上传/解析/Embedding/pgvector）、RAG 问答（混合检索 BM25+向量 RRF、引用来源、诚实原则）、扫描版 PDF OCR、多模态图片问答（粘贴截图 → 视觉模型）、文档总结、Agent Tool Calling（任务工具）、用量统计。测试 45 个（含真实 AI 调用的集成用例，CI 自动排除无 Key 用例）。
