"""异常定义"""

from typing import Optional, Any, Dict


class AppException(Exception):
    """基础异常类"""
    status_code: int = 500
    message: str = "Internal server error"
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if message:
            self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """资源不存在"""
    status_code = 404
    message = "Resource not found"
    code = "NOT_FOUND"


class ValidationError(AppException):
    """数据验证失败"""
    status_code = 400
    message = "Validation failed"
    code = "VALIDATION_ERROR"


class UnauthorizedError(AppException):
    """未授权"""
    status_code = 401
    message = "Unauthorized"
    code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    """禁止访问"""
    status_code = 403
    message = "Forbidden"
    code = "FORBIDDEN"


class BlackDuckAPIError(AppException):
    """Black Duck API 调用失败"""
    status_code = 502
    message = "Black Duck API error"
    code = "BLACK_DUCK_ERROR"


class ComponentDuplicateError(AppException):
    """组件重复"""
    status_code = 409
    message = "Component with same name and version already exists"
    code = "COMPONENT_DUPLICATE"


class InvalidStatusTransitionError(AppException):
    """非法状态转换"""
    status_code = 400
    message = "Invalid status transition"
    code = "INVALID_STATUS_TRANSITION"
