"""RAG Prompt 模板（诚实原则：只基于知识库内容回答，不足则明说）。"""

RAG_SYSTEM_PROMPT = (
    "你是一个知识库问答助手。请严格基于提供的【知识库内容】回答用户问题。\n"
    "规则：\n"
    "1. 只能使用【知识库内容】中的信息回答，不得使用你自己的知识补充或编造。\n"
    '2. 如果知识库内容不足以回答用户问题，请明确回答："知识库中没有找到足够的信息。"\n'
    "3. 回答中引用具体内容时，在句末标注来源编号，例如 [1]、[2]。\n"
)

NO_RELEVANT_CONTENT_REPLY = "知识库中没有找到足够的信息。"


def build_rag_messages(context: str, question: str) -> list[dict]:
    """组装 RAG 模式的 LLM 消息（检索结果不混入对话历史）。"""
    return [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"【知识库内容】\n{context}\n\n【用户问题】\n{question}",
        },
    ]
