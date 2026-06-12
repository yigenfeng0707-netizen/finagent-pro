import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class FinAgentException(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


class AgentExecutionError(FinAgentException):
    def __init__(self, agent_name: str, reason: str):
        super().__init__(
            message=f"Agent {agent_name} 执行失败", status_code=500, detail={"agent": agent_name, "reason": reason}
        )


class DataFetchError(FinAgentException):
    def __init__(self, source: str, reason: str):
        super().__init__(
            message=f"数据获取失败: {source}", status_code=502, detail={"source": source, "reason": reason}
        )


class LLMError(FinAgentException):
    def __init__(self, model: str, reason: str):
        super().__init__(message=f"LLM调用失败: {model}", status_code=503, detail={"model": model, "reason": reason})


async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, FinAgentException):
        logger.error(f"业务异常: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code, content={"status": "error", "error": exc.message, "detail": exc.detail}
        )

    logger.error(f"未捕获异常: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "内部服务器错误", "detail": {"message": str(exc)} if str(exc) else {}},
    )


def setup_exception_handlers(app):
    app.add_exception_handler(Exception, global_exception_handler)
    logger.info("全局异常处理已注册")
