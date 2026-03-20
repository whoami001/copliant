"""异常处理测试"""

import pytest

from app.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    BlackDuckAPIError,
    ComponentDuplicateError,
    InvalidStatusTransitionError,
)


class TestAppException:
    """基础异常测试"""

    def test_app_exception_default(self):
        """测试基础异常 - 默认值"""
        exc = AppException()
        assert exc.status_code == 500
        assert exc.message == "Internal server error"
        assert exc.code == "INTERNAL_ERROR"

    def test_app_exception_custom_message(self):
        """测试基础异常 - 自定义消息"""
        exc = AppException(message="Custom error")
        assert exc.message == "Custom error"
        assert exc.status_code == 500

    def test_app_exception_with_details(self):
        """测试基础异常 - 带详情"""
        exc = AppException(message="Error", details={"field": "value"})
        assert exc.details == {"field": "value"}

    def test_app_exception_str(self):
        """测试基础异常 - 字符串表示"""
        exc = AppException(message="Test error")
        assert str(exc) == "Test error"


class TestNotFoundError:
    """资源不存在异常测试"""

    def test_not_found_default(self):
        """测试资源不存在 - 默认值"""
        exc = NotFoundError()
        assert exc.status_code == 404
        assert exc.message == "Resource not found"
        assert exc.code == "NOT_FOUND"

    def test_not_found_custom_message(self):
        """测试资源不存在 - 自定义消息"""
        exc = NotFoundError(message="Component not found")
        assert exc.message == "Component not found"
        assert exc.status_code == 404

    def test_not_found_inheritance(self):
        """测试资源不存在 - 继承关系"""
        exc = NotFoundError()
        assert isinstance(exc, AppException)


class TestValidationError:
    """数据验证异常测试"""

    def test_validation_error_default(self):
        """测试验证异常 - 默认值"""
        exc = ValidationError()
        assert exc.status_code == 400
        assert exc.message == "Validation failed"
        assert exc.code == "VALIDATION_ERROR"

    def test_validation_error_custom_message(self):
        """测试验证异常 - 自定义消息"""
        exc = ValidationError(message="Invalid email format")
        assert exc.message == "Invalid email format"

    def test_validation_error_chinese_message(self):
        """测试验证异常 - 中文消息"""
        exc = ValidationError(message="驳回必须填写原因")
        assert exc.message == "驳回必须填写原因"

    def test_validation_error_inheritance(self):
        """测试验证异常 - 继承关系"""
        exc = ValidationError()
        assert isinstance(exc, AppException)


class TestUnauthorizedError:
    """未授权异常测试"""

    def test_unauthorized_default(self):
        """测试未授权 - 默认值"""
        exc = UnauthorizedError()
        assert exc.status_code == 401
        assert exc.message == "Unauthorized"
        assert exc.code == "UNAUTHORIZED"

    def test_unauthorized_custom_message(self):
        """测试未授权 - 自定义消息"""
        exc = UnauthorizedError(message="Token expired")
        assert exc.message == "Token expired"
        assert exc.status_code == 401


class TestForbiddenError:
    """禁止访问异常测试"""

    def test_forbidden_default(self):
        """测试禁止访问 - 默认值"""
        exc = ForbiddenError()
        assert exc.status_code == 403
        assert exc.message == "Forbidden"
        assert exc.code == "FORBIDDEN"

    def test_forbidden_custom_message(self):
        """测试禁止访问 - 自定义消息"""
        exc = ForbiddenError(message="Only admin can access this")
        assert exc.message == "Only admin can access this"
        assert exc.status_code == 403


class TestBlackDuckAPIError:
    """Black Duck API 异常测试"""

    def test_blackduck_error_default(self):
        """测试 Black Duck 异常 - 默认值"""
        exc = BlackDuckAPIError()
        assert exc.status_code == 502
        assert exc.message == "Black Duck API error"
        assert exc.code == "BLACK_DUCK_ERROR"

    def test_blackduck_error_custom_message(self):
        """测试 Black Duck 异常 - 自定义消息"""
        exc = BlackDuckAPIError(message="Connection timeout")
        assert exc.message == "Connection timeout"
        assert exc.status_code == 502


class TestComponentDuplicateError:
    """组件重复异常测试"""

    def test_duplicate_error_default(self):
        """测试组件重复 - 默认值"""
        exc = ComponentDuplicateError()
        assert exc.status_code == 409
        assert exc.message == "Component with same name and version already exists"
        assert exc.code == "COMPONENT_DUPLICATE"

    def test_duplicate_error_custom_message(self):
        """测试组件重复 - 自定义消息"""
        exc = ComponentDuplicateError(message="lodash@4.17.21 already exists")
        assert exc.message == "lodash@4.17.21 already exists"
        assert exc.status_code == 409


class TestInvalidStatusTransitionError:
    """非法状态转换异常测试"""

    def test_invalid_transition_default(self):
        """测试非法状态转换 - 默认值"""
        exc = InvalidStatusTransitionError()
        assert exc.status_code == 400
        assert exc.message == "Invalid status transition"
        assert exc.code == "INVALID_STATUS_TRANSITION"

    def test_invalid_transition_custom_message(self):
        """测试非法状态转换 - 自定义消息"""
        exc = InvalidStatusTransitionError(message="Cannot transition from draft to approved")
        assert exc.message == "Cannot transition from draft to approved"
        assert exc.status_code == 400


class TestExceptionHierarchy:
    """异常层级测试"""

    def test_all_exceptions_inherit_from_app_exception(self):
        """测试所有异常继承自 AppException"""
        exceptions = [
            NotFoundError(),
            ValidationError(),
            UnauthorizedError(),
            ForbiddenError(),
            BlackDuckAPIError(),
            ComponentDuplicateError(),
            InvalidStatusTransitionError(),
        ]

        for exc in exceptions:
            assert isinstance(exc, AppException)

    def test_all_exceptions_have_status_code(self):
        """测试所有异常都有状态码"""
        exceptions = [
            NotFoundError(),
            ValidationError(),
            UnauthorizedError(),
            ForbiddenError(),
            BlackDuckAPIError(),
            ComponentDuplicateError(),
            InvalidStatusTransitionError(),
        ]

        for exc in exceptions:
            assert hasattr(exc, "status_code")
            assert isinstance(exc.status_code, int)
            assert 400 <= exc.status_code <= 599

    def test_all_exceptions_have_code(self):
        """测试所有异常都有错误代码"""
        exceptions = [
            NotFoundError(),
            ValidationError(),
            UnauthorizedError(),
            ForbiddenError(),
            BlackDuckAPIError(),
            ComponentDuplicateError(),
            InvalidStatusTransitionError(),
        ]

        for exc in exceptions:
            assert hasattr(exc, "code")
            assert isinstance(exc.code, str)
            assert len(exc.code) > 0

    def test_all_exceptions_have_message(self):
        """测试所有异常都有消息"""
        exceptions = [
            NotFoundError(),
            ValidationError(),
            UnauthorizedError(),
            ForbiddenError(),
            BlackDuckAPIError(),
            ComponentDuplicateError(),
            InvalidStatusTransitionError(),
        ]

        for exc in exceptions:
            assert hasattr(exc, "message")
            assert isinstance(exc.message, str)
            assert len(exc.message) > 0
