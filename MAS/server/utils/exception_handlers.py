"""
自定义异常处理器
提供更友好的错误消息
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求验证错误，返回更友好的错误消息
    """
    # 提取错误详情
    errors = exc.errors()
    
    # 构建友好的错误消息
    missing_fields = []
    invalid_fields = []
    
    for error in errors:
        field_name = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
        error_type = error["type"]
        
        if error_type == "missing":
            missing_fields.append(field_name)
        else:
            invalid_fields.append({
                "field": field_name,
                "message": error["msg"],
                "type": error_type
            })
    
    # 构建响应
    error_detail = {
        "error": "Request validation failed",
        "message": "The request contains invalid or missing data.",
        "details": {}
    }
    
    if missing_fields:
        error_detail["details"]["missing_fields"] = missing_fields
        error_detail["message"] = f"Missing required fields: {', '.join(missing_fields)}"
    
    if invalid_fields:
        error_detail["details"]["invalid_fields"] = invalid_fields
    
    # 添加针对性的建议
    if "device_id" in missing_fields or "device_name" in missing_fields:
        error_detail["suggestion"] = "Please provide both 'device_id' and 'device_name' fields. These identify the device creating this knowledge base."
    elif missing_fields:
        error_detail["suggestion"] = f"Please provide all required fields: {', '.join(missing_fields)}"
    else:
        error_detail["suggestion"] = "Please check the field formats and try again."
    
    # 记录日志
    logger.warning(f"Validation error on {request.url.path}: {error_detail}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": error_detail}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    处理一般异常
    """
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    
    error_detail = {
        "error": "Internal server error",
        "message": "An unexpected error occurred while processing your request.",
        "suggestion": "Please try again later or contact support if the problem persists."
    }
    
    # 在开发环境可以包含更多错误信息
    import os
    if os.getenv("DEBUG", "").lower() == "true":
        error_detail["debug_info"] = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail}
    )
