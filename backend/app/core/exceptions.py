"""统一业务异常。

错误码分段（TDD 17.1）：
- 4xxx 业务错误
- 5xxx 系统错误
- 6xxx AI 调用错误（后续阶段使用）
"""


class AppException(Exception):
    def __init__(self, code: int, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(code=4010, message=message, http_status=401)


class NotFoundError(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=4040, message=message, http_status=404)
