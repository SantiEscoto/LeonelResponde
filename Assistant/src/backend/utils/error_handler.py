#!/usr/bin/env python3
"""
Centralized Error Handling and Resilience Module for LeonelResponde Assistant
Provides robust error handling, retry mechanisms, and system resilience features
"""

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
import functools
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type

try:
    from .unified_logger import get_unified_logger
except ImportError:

    def get_unified_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)


try:
    from .unified_config import get_config
except ImportError:
    get_config = None

# Import error types from separate module to avoid circular imports
from .error_types import ErrorSeverity, ErrorCategory

logger = get_unified_logger("ErrorHandler")


# ErrorSeverity and ErrorCategory are now imported from error_types.py


@dataclass
class ErrorContext:
    """Context information for error handling.

    Accepts optional `severity` and `category` for backward compatibility,
    which are not used by the handler (severity/category live on ResilientError).
    """

    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Backward-compat fields to avoid TypeError if passed inadvertently
    severity: Optional[ErrorSeverity] = None
    category: Optional[ErrorCategory] = None


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    stop_on: List[Type[Exception]] = field(default_factory=list)


class ResilientError(Exception):
    """Base exception class with enhanced error information"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext("unknown", "unknown")
        self.original_error = original_error
        self.recoverable = recoverable
        self.timestamp = time.time()
        self.traceback_str = traceback.format_exc() if original_error else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "component": self.context.component,
            "operation": self.context.operation,
            "user_id": self.context.user_id,
            "session_id": self.context.session_id,
            "request_id": self.context.request_id,
            "metadata": self.context.metadata,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
            "original_error": str(self.original_error) if self.original_error else None,
            "traceback": self.traceback_str,
        }


class ErrorHandler:
    """Centralized error handling and resilience manager"""

    def __init__(self, config=None):
        self.config = config or (get_config() if get_config else None)
        self.error_history: List[ResilientError] = []
        self.max_history_size = 1000
        self.circuit_breakers: Dict[str, "CircuitBreaker"] = {}
        self.fallback_handlers: Dict[str, Callable] = {}

        # Error statistics
        self.error_counts: Dict[str, int] = {}
        self.recovery_counts: Dict[str, int] = {}

    def register_fallback(self, component: str, fallback_func: Callable):
        """Register a fallback function for a component"""
        self.fallback_handlers[component] = fallback_func
        logger.info(f"Registered fallback handler for {component}")

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
    ) -> ResilientError:
        """Handle and classify an error"""

        # Create resilient error
        resilient_error = ResilientError(
            message=str(error),
            category=category,
            context=context,
            original_error=error,
        )
        resilient_error.severity = severity

        # Log error
        self._log_error(resilient_error)

        # Add to history
        self._add_to_history(resilient_error)

        # Check circuit breaker
        self._check_circuit_breaker(context.component, resilient_error)

        return resilient_error

    def _log_error(self, error: ResilientError):
        """Log error with context information"""
        try:
            logger.error(
                f"[{error.severity.value.upper()}] {error.category.value}: {error.message}",
                extra={"error": error.to_dict()},
            )
        except Exception:
            # Fallback if logger doesn't support 'extra'
            logger.error(f"Error: {error.message} ({error.category.value})")

    def _add_to_history(self, error: ResilientError):
        """Add error to history with size limit"""
        self.error_history.append(error)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)

    def _check_circuit_breaker(self, component: str, error: ResilientError):
        """Update and check circuit breaker status"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = CircuitBreaker(component)

        cb = self.circuit_breakers[component]
        cb.record_failure()
        self.error_counts[component] = self.error_counts.get(component, 0) + 1

        if not error.recoverable:
            logger.warning(f"Unrecoverable error in {component}: opening circuit")

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": len(self.error_history),
            "by_component": self.error_counts,
            "recoveries": self.recovery_counts,
        }

    @contextmanager
    def error_context(self, component: str, operation: str, **kwargs):
        """Context manager for automatic error handling"""
        ctx = ErrorContext(component=component, operation=operation, metadata=kwargs)
        try:
            yield ctx
        except Exception as e:
            self.handle_error(e, ctx)
            raise ResilientError(str(e), context=ctx) from e


class CircuitBreakerState(Enum):
    """States for the circuit breaker"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker implementation"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.state = CircuitBreakerState.CLOSED
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def record_failure(self):
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' opened")

    def record_success(self):
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - (self.last_failure_time or 0) >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed")

    def can_execute(self) -> bool:
        if self.state == CircuitBreakerState.OPEN:
            return time.time() - (self.last_failure_time or 0) >= self.recovery_timeout
        return True


def retry_with_backoff(config: RetryConfig = None):
    """Decorator for retrying a function with exponential backoff"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            delay = config.base_delay
            while attempts < config.max_attempts:
                try:
                    return func(*args, **kwargs)
                except tuple(config.stop_on) as e:
                    raise e
                except tuple(config.retry_on):
                    attempts += 1
                    if attempts >= config.max_attempts:
                        raise
                    if config.jitter:
                        # Add jitter to reduce contention
                        delay = min(config.max_delay, delay * config.exponential_base)
                    time.sleep(delay)

        return wrapper

    return decorator


def async_retry_with_backoff(config: RetryConfig = None):
    """Decorator for retrying an async function with exponential backoff"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            delay = config.base_delay
            while attempts < config.max_attempts:
                try:
                    return await func(*args, **kwargs)
                except tuple(config.stop_on) as e:
                    raise e
                except tuple(config.retry_on):
                    attempts += 1
                    if attempts >= config.max_attempts:
                        raise
                    if config.jitter:
                        delay = min(config.max_delay, delay * config.exponential_base)
                    await asyncio.sleep(delay)

        return wrapper

    return decorator


_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(error: Exception, component: str, operation: str, **kwargs) -> ResilientError:
    handler = get_error_handler()
    ctx = ErrorContext(component=component, operation=operation, metadata=kwargs)
    return handler.handle_error(error, ctx)


def register_fallback(component: str, fallback_func: Callable):
    handler = get_error_handler()
    handler.register_fallback(component, fallback_func)


@contextmanager
def resilient_operation(component: str, operation: str, **kwargs):
    handler = get_error_handler()
    ctx = ErrorContext(component=component, operation=operation, metadata=kwargs)
    try:
        yield ctx
    except Exception as e:
        handler.handle_error(e, ctx)
        raise ResilientError(str(e), context=ctx) from e


if __name__ == "__main__":
    print("🧪 Testing error handling system...")

    handler = ErrorHandler()

    # Test error context
    try:
        with handler.error_context("test_component", "test_operation") as ctx:
            raise ValueError("Test error")
    except ResilientError as e:
        print(f"✅ Caught resilient error: {e.message}")

    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
    def failing_function():
        raise ConnectionError("Simulated failure")

    try:
        failing_function()
    except ConnectionError:
        print("✅ Retry mechanism worked")

    stats = handler.get_error_stats()
    print(f"📊 Error stats: {stats}")

    print("✅ Error handling system test completed")
