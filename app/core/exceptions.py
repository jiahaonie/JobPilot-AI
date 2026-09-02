"""领域异常及其 HTTP 转换。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """可安全暴露给 API 客户端的错误基类。"""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ResourceNotFoundError(DomainError):
    """请求的领域资源不存在时抛出。"""

    status_code = 404


class LLMAnalysisError(DomainError):
    """大语言模型分析无法生成有效结果时抛出。"""

    status_code = 503


class AnalysisPersistenceError(DomainError):
    """分析结果无法可靠保存时抛出。"""

    status_code = 500


class ResumeAnalysisNotReadyError(DomainError):
    """简历分析成功前请求匹配时抛出。"""

    status_code = 409


class UnsupportedFileTypeError(DomainError):
    """上传文件格式不在支持范围内时抛出。"""

    status_code = 415


class FileTooLargeError(DomainError):
    """上传内容超过配置的字节限制时抛出。"""

    status_code = 413


class InvalidFileError(DomainError):
    """允许的文件无法生成可用简历文本时抛出。"""

    status_code = 422


class JobRequirementNotFoundError(DomainError):
    """匹配尚无已保存分析的岗位时抛出。"""

    status_code = 404


class GroundingValidationError(DomainError):
    """回答引用检索上下文之外的证据时抛出。"""

    status_code = 502


def register_exception_handlers(application: FastAPI) -> None:
    """为领域层失败注册一致的响应。"""

    @application.exception_handler(DomainError)
    async def handle_domain_error(
        _request: Request,
        exc: DomainError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
