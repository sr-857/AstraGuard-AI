"""
Unit tests for core/error_handling.py

Tests custom exceptions, error classification, safe execution utilities,
and error context management.
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import patch, MagicMock

from core.error_handling import (
    AstraGuardException,
    ModelLoadError,
    AnomalyEngineError,
    PolicyEvaluationError,
    StateTransitionError,
    MemoryEngineError,
    ErrorSeverity,
    ErrorContext,
    classify_error,
    log_error,
    handle_component_error,
    safe_execute,
    ErrorContext_ContextManager,
)


class TestCustomExceptions:
    """Test custom exception hierarchy"""

    def test_astraguard_exception_initialization(self):
        """Test AstraGuardException initialization"""
        exc = AstraGuardException("Test error", "test_component", {"key": "value"})
        assert str(exc) == "Test error"
        assert exc.component == "test_component"
        assert exc.context == {"key": "value"}
        assert isinstance(exc.timestamp, datetime)

    def test_astraguard_exception_to_dict(self):
        """Test AstraGuardException to_dict method"""
        exc = AstraGuardException("Test error", "test_component")
        data = exc.to_dict()
        assert data["error_type"] == "AstraGuardException"
        assert data["message"] == "Test error"
        assert data["component"] == "test_component"
        assert "timestamp" in data

    def test_specific_exceptions_inherit(self):
        """Test that specific exceptions inherit from AstraGuardException"""
        exceptions = [
            ModelLoadError("Model failed"),
            AnomalyEngineError("Anomaly failed"),
            PolicyEvaluationError("Policy failed"),
            StateTransitionError("Transition failed"),
            MemoryEngineError("Memory failed"),
        ]

        for exc in exceptions:
            assert isinstance(exc, AstraGuardException)
            assert exc.component == "unknown"  # default


class TestErrorContext:
    """Test ErrorContext dataclass"""

    def test_initialization(self):
        """Test ErrorContext initialization"""
        ctx = ErrorContext(
            error_type="ValueError",
            component="test_comp",
            message="Test message",
            severity=ErrorSeverity.HIGH,
            original_exception=ValueError("test"),
            context_data={"key": "value"}
        )

        assert ctx.error_type == "ValueError"
        assert ctx.component == "test_comp"
        assert ctx.message == "Test message"
        assert ctx.severity == ErrorSeverity.HIGH
        assert isinstance(ctx.original_exception, ValueError)
        assert ctx.context_data == {"key": "value"}
        assert isinstance(ctx.timestamp, datetime)

    def test_default_values(self):
        """Test ErrorContext default values"""
        ctx = ErrorContext(
            error_type="Exception",
            component="test",
            message="msg",
            severity=ErrorSeverity.LOW
        )

        assert ctx.context_data == {}
        assert isinstance(ctx.timestamp, datetime)
        assert ctx.original_exception is None

    def test_to_dict(self):
        """Test ErrorContext to_dict method"""
        ctx = ErrorContext(
            error_type="ValueError",
            component="test",
            message="Test message",
            severity=ErrorSeverity.MEDIUM,
            context_data={"key": "value"}
        )

        data = ctx.to_dict()
        assert data["error_type"] == "ValueError"
        assert data["component"] == "test"
        assert data["message"] == "Test message"
        assert data["severity"] == "medium"
        assert data["context"] == {"key": "value"}
        assert "timestamp" in data


class TestClassifyError:
    """Test error classification functionality"""

    def test_classify_astraguard_exceptions(self):
        """Test classification of AstraGuard exceptions"""
        test_cases = [
            (ModelLoadError("Model failed"), ErrorSeverity.HIGH),
            (AnomalyEngineError("Anomaly failed"), ErrorSeverity.MEDIUM),
            (PolicyEvaluationError("Policy failed"), ErrorSeverity.MEDIUM),
            (StateTransitionError("Transition failed"), ErrorSeverity.HIGH),
            (MemoryEngineError("Memory failed"), ErrorSeverity.MEDIUM),
        ]

        for exc, expected_severity in test_cases:
            ctx = classify_error(exc, "test_component")
            assert ctx.error_type == exc.__class__.__name__
            assert ctx.component == "test_component"
            assert ctx.message == str(exc)
            assert ctx.severity == expected_severity
            assert ctx.original_exception is exc

    def test_classify_standard_exceptions(self):
        """Test classification of standard Python exceptions"""
        test_cases = [
            (ValueError("Invalid value"), ErrorSeverity.MEDIUM),
            (KeyError("Missing key"), ErrorSeverity.MEDIUM),
            (Exception("Generic error"), ErrorSeverity.HIGH),
        ]

        for exc, expected_severity in test_cases:
            ctx = classify_error(exc, "test_component")
            assert ctx.error_type == exc.__class__.__name__
            assert ctx.component == "test_component"
            assert ctx.message == str(exc)
            assert ctx.severity == expected_severity

    def test_classify_with_context(self):
        """Test classification with additional context"""
        exc = ValueError("Test error")
        context = {"operation": "test_op", "phase": "launch"}

        ctx = classify_error(exc, "test_component", context)
        assert ctx.context_data == context


class TestLogError:
    """Test error logging functionality"""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return MagicMock(spec=logging.Logger)

    def test_log_critical_error(self, mock_logger):
        """Test logging critical severity error"""
        ctx = ErrorContext(
            error_type="Exception",
            component="test",
            message="Critical error",
            severity=ErrorSeverity.CRITICAL
        )

        log_error(ctx, mock_logger)
        mock_logger.critical.assert_called_once()
        call_args = mock_logger.critical.call_args
        assert "CRITICAL ERROR in test: Critical error" in call_args[0][0]

    def test_log_high_error(self, mock_logger):
        """Test logging high severity error"""
        ctx = ErrorContext(
            error_type="Exception",
            component="test",
            message="High error",
            severity=ErrorSeverity.HIGH
        )

        log_error(ctx, mock_logger)
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "ERROR in test: High error" in call_args[0][0]

    def test_log_medium_error(self, mock_logger):
        """Test logging medium severity error"""
        ctx = ErrorContext(
            error_type="Exception",
            component="test",
            message="Medium error",
            severity=ErrorSeverity.MEDIUM
        )

        log_error(ctx, mock_logger)
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "WARNING in test: Medium error" in call_args[0][0]

    def test_log_low_error(self, mock_logger):
        """Test logging low severity error"""
        ctx = ErrorContext(
            error_type="Exception",
            component="test",
            message="Low error",
            severity=ErrorSeverity.LOW
        )

        log_error(ctx, mock_logger)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "INFO from test: Low error" in call_args[0][0]

    def test_log_with_default_logger(self):
        """Test logging with default logger"""
        ctx = ErrorContext(
            error_type="Exception",
            component="test",
            message="Test error",
            severity=ErrorSeverity.HIGH
        )

        with patch('core.error_handling.logger') as mock_default_logger:
            log_error(ctx)
            mock_default_logger.error.assert_called_once()


class TestHandleComponentError:
    """Test handle_component_error decorator"""

    def test_decorator_success(self):
        """Test decorator when function succeeds"""
        @handle_component_error("test_component")
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_decorator_astraguard_exception(self):
        """Test decorator with AstraGuard exception"""
        @handle_component_error("test_component", fallback_value="fallback")
        def failing_func():
            raise ModelLoadError("Model failed")

        with patch('core.error_handling.logger') as mock_logger:
            result = failing_func()
            assert result == "fallback"
            mock_logger.error.assert_called_once()

    def test_decorator_generic_exception(self):
        """Test decorator with generic exception"""
        @handle_component_error("test_component", fallback_value="fallback")
        def failing_func():
            raise ValueError("Generic error")

        with patch('core.error_handling.logger') as mock_logger:
            result = failing_func()
            assert result == "fallback"
            mock_logger.warning.assert_called_once()

    def test_decorator_custom_severity(self):
        """Test decorator with custom severity"""
        @handle_component_error("test_component", severity=ErrorSeverity.CRITICAL)
        def failing_func():
            raise Exception("Critical error")

        with patch('core.error_handling.logger') as mock_logger:
            failing_func()
            mock_logger.critical.assert_called_once()

    def test_decorator_no_traceback_logging(self):
        """Test decorator with traceback logging disabled"""
        @handle_component_error("test_component", log_traceback=False)
        def failing_func():
            raise Exception("Error")

        with patch('core.error_handling.logger') as mock_logger:
            failing_func()
            # Should not log debug traceback
            mock_logger.debug.assert_not_called()


class TestSafeExecute:
    """Test safe_execute function"""

    def test_safe_execute_success(self):
        """Test safe_execute with successful function"""
        def success_func(x, y):
            return x + y

        result = safe_execute(success_func, 2, 3, component="test")
        assert result == 5

    def test_safe_execute_astraguard_exception(self):
        """Test safe_execute with AstraGuard exception"""
        def failing_func():
            raise ModelLoadError("Model failed")

        with patch('core.error_handling.logger') as mock_logger:
            result = safe_execute(failing_func, component="test", fallback_value="fallback")
            assert result == "fallback"
            mock_logger.error.assert_called_once()

    def test_safe_execute_generic_exception(self):
        """Test safe_execute with generic exception"""
        def failing_func():
            raise ValueError("Generic error")

        with patch('core.error_handling.logger') as mock_logger:
            result = safe_execute(failing_func, component="test", fallback_value="fallback")
            assert result == "fallback"
            mock_logger.warning.assert_called_once()

    def test_safe_execute_with_context(self):
        """Test safe_execute with additional context"""
        def failing_func():
            raise Exception("Error")

        context = {"operation": "test_op"}

        with patch('core.error_handling.logger') as mock_logger:
            safe_execute(failing_func, component="test", context=context)
            # Verify context is included in logging
            call_args = mock_logger.error.call_args
            assert "operation" in str(call_args)


class TestErrorContextContextManager:
    """Test ErrorContext_ContextManager"""

    def test_context_manager_success(self):
        """Test context manager with no exceptions"""
        with ErrorContext_ContextManager("test_component") as ctx:
            pass
        assert ctx.error_ctx is None

    def test_context_manager_exception_handled(self):
        """Test context manager that handles exceptions"""
        with patch('core.error_handling.logger') as mock_logger:
            with ErrorContext_ContextManager("test_component", default_return="fallback") as ctx:
                raise ValueError("Test error")

            assert ctx.error_ctx is not None
            assert ctx.error_ctx.error_type == "ValueError"
            assert ctx.error_ctx.component == "test_component"
            mock_logger.warning.assert_called_once()

    def test_context_manager_exception_reraised(self):
        """Test context manager that reraises exceptions"""
        with patch('core.error_handling.logger') as mock_logger:
            with pytest.raises(ValueError):
                with ErrorContext_ContextManager("test_component", reraise=True) as ctx:
                    raise ValueError("Test error")

            assert ctx.error_ctx is not None
            mock_logger.warning.assert_called_once()

    def test_context_manager_on_error_callback(self):
        """Test context manager with on_error callback"""
        callback_called = False
        error_ctx_received = None

        def on_error_callback(error_ctx):
            nonlocal callback_called, error_ctx_received
            callback_called = True
            error_ctx_received = error_ctx

        with patch('core.error_handling.logger'):
            with ErrorContext_ContextManager("test_component", on_error=on_error_callback) as ctx:
                raise Exception("Test error")

            assert callback_called
            assert error_ctx_received is not None
            assert error_ctx_received.error_type == "Exception"

    def test_context_manager_traceback_logging(self):
        """Test that context manager logs traceback"""
        with patch('core.error_handling.logger') as mock_logger:
            with ErrorContext_ContextManager("test_component") as ctx:
                raise Exception("Test error")

            mock_logger.debug.assert_called_once()
            debug_call = mock_logger.debug.call_args[0][0]
            assert "Traceback:" in debug_call


class TestErrorSeverity:
    """Test ErrorSeverity enum"""

    def test_severity_values(self):
        """Test that all severity levels are defined"""
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.LOW.value == "low"

    def test_severity_ordering(self):
        """Test severity level ordering"""
        assert ErrorSeverity.CRITICAL > ErrorSeverity.HIGH
        assert ErrorSeverity.HIGH > ErrorSeverity.MEDIUM
        assert ErrorSeverity.MEDIUM > ErrorSeverity.LOW
