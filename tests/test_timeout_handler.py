"""
Tests for timeout handler functionality.

Validates:
- Timeout enforcement on long-running operations
- Async timeout with asyncio.wait_for
- Timeout exception handling
- Integration with existing resilience patterns
"""

import pytest
import asyncio
import time
from core.timeout_handler import (
    with_timeout,
    async_timeout,
    TimeoutContext,
    TimeoutError as CustomTimeoutError,
    get_timeout_config,
)


class TestTimeoutDecorator:
    """Test synchronous timeout decorator"""
    
    def test_operation_within_timeout(self):
        """Test that fast operations complete successfully"""
        @with_timeout(seconds=2.0)
        def fast_operation():
            time.sleep(0.1)
            return "success"
        
        result = fast_operation()
        assert result == "success"
    
    def test_operation_exceeds_timeout(self):
        """Test that slow operations raise Timeout Error"""
        @with_timeout(seconds=0.5)
        def slow_operation():
            time.sleep(2.0)
            return "should_not_reach"
        
        with pytest.raises(CustomTimeoutError) as exc_info:
            slow_operation()
        
        assert "slow_operation" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)
    
    def test_timeout_with_custom_name(self):
        """Test timeout with custom operation name"""
        @with_timeout(seconds=0.5, operation_name="my_custom_op")
        def operation():
            time.sleep(2.0)
        
        with pytest.raises(CustomTimeoutError) as exc_info:
            operation()
        
        assert "my_custom_op" in str(exc_info.value)
    
    def test_timeout_error_contains_metadata(self):
        """Test that TimeoutError includes useful metadata"""
        @with_timeout(seconds=0.5)
        def operation():
            time.sleep(2.0)
        
        try:
            operation()
            pytest.fail("Should have raised TimeoutError")
        except CustomTimeoutError as e:
            assert e.operation == "operation"
            assert e.timeout_seconds == 0.5
            assert e.start_time is not None


class TestAsyncTimeout:
    """Test asynchronous timeout decorator"""
    
    @pytest.mark.asyncio
    async def test_async_operation_within_timeout(self):
        """Test that fast async operations complete successfully"""
        @async_timeout(seconds=2.0)
        async def fast_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await fast_operation()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_operation_exceeds_timeout(self):
        """Test that slow async operations raise TimeoutError"""
        @async_timeout(seconds=0.5)
        async def slow_operation():
            await asyncio.sleep(2.0)
            return "should_not_reach"
        
        with pytest.raises(CustomTimeoutError) as exc_info:
            await slow_operation()
        
        assert "slow_operation" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_async_timeout_with_custom_name(self):
        """Test async timeout with custom operation name"""
        @async_timeout(seconds=0.5, operation_name="async_custom_op")
        async def operation():
            await asyncio.sleep(2.0)
        
        with pytest.raises(CustomTimeoutError) as exc_info:
            await operation()
        
        assert "async_custom_op" in str(exc_info.value)


class TestTimeoutContext:
    """Test timeout context manager"""
    
    def test_context_within_timeout(self):
        """Test that fast operations complete successfully"""
        with TimeoutContext(seconds=2.0, operation="test_op"):
            time.sleep(0.1)
        # Should complete without exception
    
    def test_context_exceeds_timeout(self):
        """Test that slow operations raise timeout"""
        with pytest.raises(CustomTimeoutError):
            with TimeoutContext(seconds=0.5, operation="slow_op"):
                time.sleep(2.0)
    
    def test_context_manual_check(self):
        """Test manual timeout checking"""
        ctx = TimeoutContext(seconds=0.5, operation="check_op")
        ctx.__enter__()
        
        # Fast check - should not raise
        ctx.check_timeout()
        
        time.sleep(0.6)  # Exceed timeout
        
        with pytest.raises(CustomTimeoutError):
            ctx.check_timeout()
        
        ctx.__exit__(None, None, None)


class TestTimeoutConfig:
    """Test timeout configuration loading"""
    
    def test_config_loads_defaults(self):
        """Test that config loads with default values"""
        config = get_timeout_config()
        
        assert config.model_load_timeout > 0
        assert config.inference_timeout > 0
        assert config.redis_timeout > 0
        assert config.file_io_timeout > 0
    
    def test_config_singleton(self):
        """Test that get_timeout_config returns same instance"""
        config1 = get_timeout_config()
        config2 = get_timeout_config()
        
        assert config1 is config2


class TestTimeoutIntegration:
    """Test timeout integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """Test timeout works with retry logic"""
        from core.retry import Retry
        
        call_count = 0
        
        @Retry(max_attempts=3, base_delay=0.1)
        @async_timeout(seconds=0.5)
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                await asyncio.sleep(1.0)  # Will timeout
            return "success"
        
        # Should timeout on first attempt, succeed on retry
        result = await flaky_operation()
        assert result == "success"
        assert call_count == 2
    
    def test_timeout_preserves_exception(self):
        """Test that timeout doesn't swallow other exceptions"""
        @with_timeout(seconds=2.0)
        def error_operation():
            raise ValueError("custom error")
        
        with pytest.raises(ValueError) as exc_info:
            error_operation()
        
        assert "custom error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_async_timeout_preserves_exception(self):
        """Test that async timeout doesn't swallow other exceptions"""
        @async_timeout(seconds=2.0)
        async def error_operation():
            raise ValueError("async custom error")
        
        with pytest.raises(ValueError) as exc_info:
            await error_operation()
        
        assert "async custom error" in str(exc_info.value)
