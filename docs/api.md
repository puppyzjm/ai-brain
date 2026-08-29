# AI Brain API 文档

> 全部接口均为项目实际实现。统一前缀 `/api/v1`（`/health`、`/` 除外）。
> 鉴权：除注册/登录/健康检查外，均需 `Authorization: Bearer <JWT>`。
> 统一响应格式：`{"code": 0, "message": "ok", "data": ...}`；错误 `{"code": 4xxx, "message": "...", "data": null}`。

## 0. 健康检查与根路径

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查：`{"status":"ok","database":"ok","redis":"ok"}`（异常时 503） |
| GET | `/` | 应用信息：`{"app":"AI Brain API","version":"0.1.0"}` |

## 1. 认证 auth

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| POST | `/auth/register` | `{username(3-50), email(可选), password(6-128)}` | 注册，返回用户资料 |
| POST | `/auth/login` | `{account(用户名或邮箱), password}` | 登录，返回 `{access_token, token_type:"bearer"}`（JWT，7 天） |

错误码：4001 用户名已存在(409) / 4002 邮箱已被注册(409) / 4003 用户名或密码错误(401)

## 2. 用户 users

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/users/me` | 当前用户资料：`{id, username, email, role, created_at}` |

错误码：4010 未登录或 Token 无效(401)

## 3. 对话 chat（SSE）

| 方法 | 路径 | 请求体 | 说明 |
|---|---|---|---|
| POST | `/chat` | `{conversation_id?(不传新建), content, knowledge_base_ids?(可选)}` | 普通对话 / Agent / RAG 三种模式统一入口，SSE 流式响应 |

**SSE 事件类型**：

| type | 字段 | 说明 |
|---|---|---|
| `delta` | `content` | 回答文本片段（流式） |
| `tool` | `name, status(running/done/failed), message?` | Agent 工具调用状态 |
| `sources` | `sources[]` | RAG 引用来源（`filename/similarity/content_preview/page`） |
| `done` | `conversation_id, message_id, usage, error?` | 结束（含 token 用量） |
| `error` | `message` | 错误信息 |

**三种模式**：
- 不传 `knowledge_base_ids`：Agent 模式（自动携带 5 个工具，模型自主调用）+ 多轮历史；
- 传 `knowledge_base_ids`：RAG 模式（检索→Context→回答+来源；检索不足返回固定话术，不调 LLM）。

## 4. 会话 conversations

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/conversations` | — | 会话列表（按更新时间倒序） |
| POST | `/conversations` | `{title?}` | 新建会话 |
| PATCH | `/conversations/{id}` | `{title}` | 重命名 |
| DELETE | `/conversations/{id}` | — | 删除（软删） |
| GET | `/conversations/{id}/messages` | — | 历史消息（`[{id, role, content, model, created_at}]`） |

## 5. 知识库 knowledge-bases

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/knowledge-bases` | — | 列表 |
| POST | `/knowledge-bases` | `{name, description?}` | 创建 |
| PATCH | `/knowledge-bases/{id}` | `{name, description?}` | 更新 |
| DELETE | `/knowledge-bases/{id}` | — | 删除（软删） |

## 6. 文档 documents

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| POST | `/knowledge-bases/{kb_id}/documents` | multipart `file`（pdf/txt/md，≤20MB） | 上传；异步解析（uploaded→parsing→ready/failed） |
| GET | `/knowledge-bases/{kb_id}/documents` | — | 文档列表（含 `status/chunk_count/error_message`） |
| DELETE | `/documents/{id}` | — | 删除（软删 + 物理删向量） |
| POST | `/documents/{id}/reprocess` | — | 重新解析（失败重试/重启恢复） |
| POST | `/documents/{id}/summarize` | — | AI 文档总结，返回 `{document_id, summary}`（Markdown 结构化摘要） |

错误码：4004 文件类型不支持 / 4005 超过 20MB / 4006 未解析完成 / 4007 无可总结内容 / 6002 未配置 Embedding Key / 6003 AI 总结失败

## 7. 任务 tasks

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/tasks` | `?status=&priority=`（可选筛选） | 任务列表 |
| POST | `/tasks` | `{title, description?, status?, priority?, due_date?}` | 创建 |
| PATCH | `/tasks/{id}` | 部分字段 | 更新 |
| DELETE | `/tasks/{id}` | — | 删除（软删） |

枚举：status = `todo/in_progress/done`；priority = `high/medium/low`

## 8. 统计 stats

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/stats/usage` | 个人用量：`summary`（总请求/成功率/token/平均耗时）+ `by_type`（chat/rag/agent/summary）+ `daily`（近 7 天） |

## 9. Agent 工具（由模型通过 Function Calling 调用，非 HTTP 接口）

| 工具 | 参数 | 底层 |
|---|---|---|
| `create_task` | title, description?, priority?, due_date? | TaskService |
| `list_tasks` | status?, priority? | TaskService |
| `update_task` | task_id, title?/status?/priority?/due_date? | TaskService |
| `delete_task` | task_id | TaskService |
| `search_knowledge` | query, knowledge_base_ids[] | Phase 5 RAG 检索（user_id 隔离） |

## 10. 通用错误码

| code | HTTP | 含义 |
|---|---|---|
| 4010 | 401 | 未登录/Token 无效 |
| 4040 | 404 | 资源不存在（含越权访问他人资源） |
| 4220 | 422 | 参数校验失败 |
| 4001~4007 | 409/400 | 业务错误（见各节） |
| 6001/6002 | 503 | 未配置 DEEPSEEK/EMBEDDING API Key |
| 6003 | 502 | AI 调用失败 |
