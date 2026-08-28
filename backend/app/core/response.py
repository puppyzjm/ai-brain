"""统一成功响应包装（TDD 16.1：{code, message, data}）。"""
from typing import Any


def ok(data: Any = None) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}
