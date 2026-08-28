"""Phase 5 RAG 单元测试（纯函数，不依赖 AI API Key）。"""
from app.rag.context import build_context
from app.rag.prompts import NO_RELEVANT_CONTENT_REPLY, build_rag_messages

_CHUNKS = [
    {
        "chunk_id": 1,
        "document_id": 10,
        "knowledge_base_id": 100,
        "content": "FastAPI 是一个现代、快速的 Web 框架。" * 10,
        "metadata": {"page": 1},
        "filename": "fastapi.txt",
        "similarity": 0.92,
    },
    {
        "chunk_id": 2,
        "document_id": 10,
        "knowledge_base_id": 100,
        "content": "依赖注入是 FastAPI 的核心特性。" * 10,
        "metadata": {"page": 2},
        "filename": "fastapi.txt",
        "similarity": 0.81,
    },
]


def test_build_context_returns_context_and_sources() -> None:
    context, sources = build_context(_CHUNKS)
    assert "FastAPI" in context
    assert "[来源1]" in context
    assert "[来源2]" in context
    assert len(sources) == 2
    assert sources[0]["filename"] == "fastapi.txt"
    assert sources[0]["page"] == 1
    assert sources[0]["similarity"] == 0.92
    assert "content_preview" in sources[0]


def test_build_context_truncates_when_exceeds_limit() -> None:
    big_chunks = []
    for i in range(10):
        big_chunks.append(
            {
                **{k: v for k, v in _CHUNKS[0].items()},
                "chunk_id": 100 + i,
                "content": f"第{i}段内容。" * 300,  # 每段约 1800 字符
            }
        )
    context, sources = build_context(big_chunks)
    assert len(context) <= 4300  # 4000 上限 + 来源标注的少量额外字符
    assert len(sources) < 10


def test_build_rag_messages_structure() -> None:
    messages = build_rag_messages("知识内容", "问题？")
    assert messages[0]["role"] == "system"
    assert "知识库内容" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "【知识库内容】" in messages[1]["content"]
    assert "【用户问题】" in messages[1]["content"]
    assert "知识内容" in messages[1]["content"]
    assert "问题？" in messages[1]["content"]


def test_no_relevant_content_reply_is_explicit() -> None:
    assert "没有找到足够的信息" in NO_RELEVANT_CONTENT_REPLY
