#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Logging System for LeonelResponde Assistant

This module provides a unified logging system that combines:
- Structured JSON logging capabilities
- Traditional colored console logging
- Performance metrics tracking
- Request/response logging
- Error tracking with context
- Resource usage monitoring
- Backward compatibility with existing loggers

Author: LeonelResponde Team
Date: 2025-01-25
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import threading
import time
import traceback
from typing import Any, Dict, Generator, Optional, cast

# Third-party imports
# Declare color types that will be assigned depending on availability
Fore: Any
Style: Any
try:
    from colorama import Fore as _Fore, Style as _Style, init as _init

    _init(autoreset=True)
    COLORAMA_AVAILABLE = True
    # Assign imported color classes
    Fore = _Fore
    Style = _Style
except ImportError:
    COLORAMA_AVAILABLE = False

    # Fallback colors (class-level attributes for compatibility)
    class _FallbackFore:
        CYAN = YELLOW = RED = GREEN = MAGENTA = BLUE = WHITE = ""

    class _FallbackStyle:
        BRIGHT = RESET_ALL = ""

    # Assign fallbacks with permissive typing
    Fore = cast(Any, _FallbackFore)
    Style = cast(Any, _FallbackStyle)


@dataclass
class LogMetrics:
    """Data class for tracking performance metrics"""

    timestamp: str
    operation: str
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    tokens_processed: Optional[int] = None
    error_count: int = 0
    success: bool = True
    context: Optional[Dict[str, Any]] = None


class UnifiedFormatter(logging.Formatter):
    """Unified formatter that supports both JSON and colored console output"""

    def __init__(self, format_type: str = "console", use_colors: bool = True) -> None:
        super().__init__()
        self.format_type = format_type
        self.use_colors = use_colors and COLORAMA_AVAILABLE

        self.COLORS: Dict[str, str] = {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
        }

        self.ICONS: Dict[str, str] = {
            "DEBUG": "🔍",
            "INFO": "📝",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "💥",
        }

    def format(self, record: logging.LogRecord) -> str:
        if self.format_type == "json":
            return self._format_json(record)
        else:
            return self._format_console(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        exc_info = record.exc_info
        if exc_info is not None:
            exc_type, exc, tb = exc_info
            type_name: str
            if isinstance(exc_type, type) and issubclass(exc_type, BaseException):
                type_name = exc_type.__name__
            else:
                type_name = "Exception"
            log_entry["exception"] = {
                "type": type_name,
                "message": str(exc) if exc is not None else "",
                "traceback": traceback.format_exception(exc_type, exc, tb),
            }

        # Add custom fields from extra
        if hasattr(record, "extra_fields"):
            extra_fields = cast(Dict[str, Any], getattr(record, "extra_fields"))
            log_entry.update(extra_fields)

        return json.dumps(log_entry, ensure_ascii=False, default=str)

    def _format_console(self, record: logging.LogRecord) -> str:
        """Format log record for console with colors and icons"""
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        if self.use_colors:
            log_color = self.COLORS.get(record.levelname, Fore.WHITE)
            icon = self.ICONS.get(record.levelname, "📋")
            level_colored = f"{log_color}{record.levelname}{Style.RESET_ALL}"
            name_colored = f"{Fore.BLUE}{record.name}{Style.RESET_ALL}"

            return f"{timestamp} | {icon} {level_colored} | {name_colored} | {record.getMessage()}"
        else:
            return f"{timestamp} | {record.levelname} | {record.name} | {record.getMessage()}"


class MetricsTracker:
    """Thread-safe metrics tracking for performance monitoring"""

    def __init__(self) -> None:
        self._operations: Dict[str, Dict[str, Any]] = {}
        self._completed_operations: list[LogMetrics] = []
        self._lock = threading.Lock()

    def start_operation(self, operation_id: str, operation_name: str, **context: Any) -> None:
        """Start tracking an operation"""
        with self._lock:
            self._operations[operation_id] = {
                "name": operation_name,
                "start_time": time.time(),
                "context": dict(context),
            }

    def end_operation(
        self, operation_id: str, success: bool = True, context: Optional[Dict[str, Any]] = None
    ) -> Optional[LogMetrics]:
        """End tracking an operation and return metrics"""
        with self._lock:
            if operation_id not in self._operations:
                return None

            op_data = self._operations.pop(operation_id)
            duration_ms = (time.time() - op_data["start_time"]) * 1000

            # Merge contexts
            final_context = dict(op_data.get("context", {}))
            if context:
                final_context.update(context)

            metrics = LogMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                operation=op_data["name"],
                duration_ms=duration_ms,
                success=success,
                context=final_context if final_context else None,
            )

            self._completed_operations.append(metrics)
            return metrics

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all completed operations"""
        with self._lock:
            if not self._completed_operations:
                return {"total_operations": 0}

            total_ops = len(self._completed_operations)
            successful_ops = sum(1 for op in self._completed_operations if op.success)
            avg_duration = sum(op.duration_ms for op in self._completed_operations) / total_ops

            return {
                "total_operations": total_ops,
                "successful_operations": successful_ops,
                "failed_operations": total_ops - successful_ops,
                "success_rate": successful_ops / total_ops * 100,
                "average_duration_ms": avg_duration,
                "operations_by_type": self._group_by_operation(),
            }

    def _group_by_operation(self) -> Dict[str, Dict[str, Any]]:
        """Group metrics by operation type"""
        grouped: Dict[str, Dict[str, Any]] = {}
        for op in self._completed_operations:
            if op.operation not in grouped:
                grouped[op.operation] = {"count": 0, "total_duration_ms": 0.0, "success_count": 0}

            grouped[op.operation]["count"] += 1
            grouped[op.operation]["total_duration_ms"] += op.duration_ms
            if op.success:
                grouped[op.operation]["success_count"] += 1

        # Calculate averages
        for op_name, data in grouped.items():
            data["average_duration_ms"] = data["total_duration_ms"] / data["count"]
            data["success_rate"] = data["success_count"] / data["count"] * 100

        return grouped


class UnifiedLogger:
    """Unified logger that combines structured and traditional logging.

    Developer notes:
    - Reserved kwargs: exc_info, stack_info, stacklevel, extra.
      These are forwarded directly to Python's logging.Logger and not treated as structured fields.
    - Structured fields merge: any remaining keyword arguments (i.e., not reserved)
      are merged into a dedicated dictionary stored under extra["extra_fields"].
      If an "extra" dict is supplied, its non-"extra_fields" keys are also merged
      into extra_fields so they appear in structured outputs.
    - Positional args (*args) are forwarded to support classic %-style formatting for
      backward compatibility with existing logging calls, e.g. logger.info("msg %s", "x").
    - logger.exception(...) behaves like logging.Logger.exception and defaults to
      exc_info=True unless explicitly overridden.
    """

    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        enable_json_logging: bool = True,
        enable_metrics: bool = True,
    ) -> None:
        self.name = name
        self.enable_json_logging = enable_json_logging
        self.enable_metrics = enable_metrics

        # Initialize metrics tracker reference (set only if enabled)
        self.metrics: Optional[MetricsTracker] = None
        if self.enable_metrics:
            self.metrics = MetricsTracker()

        # Setup Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()

        self._setup_handlers(log_file)

    def _setup_handlers(self, log_file: Optional[str]) -> None:
        """Setup logging handlers for console and file output"""
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = UnifiedFormatter("console", use_colors=True)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handlers if log_file is specified
        if log_file:
            try:
                # Create logs directory
                current_dir = Path(__file__).parent.parent.parent
                logs_dir = current_dir / "logs"
                logs_dir.mkdir(exist_ok=True)

                # JSON log file (structured)
                if self.enable_json_logging:
                    json_file_path = logs_dir / f"{log_file.replace('.log', '')}_structured.json"
                    json_handler = logging.FileHandler(json_file_path, encoding="utf-8")
                    json_handler.setLevel(logging.DEBUG)
                    json_formatter = UnifiedFormatter("json")
                    json_handler.setFormatter(json_formatter)
                    self.logger.addHandler(json_handler)

                # Traditional text log file
                text_file_path = logs_dir / log_file
                text_handler = logging.FileHandler(text_file_path, encoding="utf-8")
                text_handler.setLevel(logging.DEBUG)
                text_formatter = UnifiedFormatter("console", use_colors=False)
                text_handler.setFormatter(text_formatter)
                self.logger.addHandler(text_handler)

            except Exception as e:
                print(f"⚠️ Could not create log files: {e}")

    # Standard logging methods
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a DEBUG level message.
        Accepts additional positional and keyword arguments for compatibility.
        Positional args are forwarded to the underlying logging call for %-style formatting.
        Non-reserved keyword args are captured as structured fields; reserved logging kwargs
        (e.g., exc_info, stack_info, stacklevel, extra) are forwarded to logging.
        """
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an INFO level message.
        Accepts additional positional and keyword arguments for compatibility.
        See debug() for forwarding behavior details.
        """
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a WARNING level message.
        Accepts additional positional and keyword arguments for compatibility.
        See debug() for forwarding behavior details.
        """
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an ERROR level message.
        Accepts additional positional and keyword arguments for compatibility.
        See debug() for forwarding behavior details.
        """
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a CRITICAL level message.
        Accepts additional positional and keyword arguments for compatibility.
        See debug() for forwarding behavior details.
        """
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an ERROR level message with exception information.
        This mirrors logging.Logger.exception by setting exc_info=True by default
        unless explicitly provided. Additional positional and keyword arguments
        are forwarded for compatibility.
        """
        # Ensure traceback is included unless explicitly overridden
        kwargs.setdefault("exc_info", True)
        self._log(logging.ERROR, message, *args, **kwargs)

    def _log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        """Internal logging method with structured data support and compatibility.

        - Positional args are forwarded for %-style message formatting used by logging.
        - Reserved kwargs (exc_info, stack_info, stacklevel, extra) are forwarded as-is.
        - Remaining kwargs are treated as structured fields and injected into `extra` under
          the key `extra_fields` so formatters can consume them. If an `extra` dict is
          supplied, its non-`extra_fields` keys are merged into the structured fields.
        """
        # Separate reserved logging kwargs from structured fields
        reserved_keys = {"exc_info", "stack_info", "stacklevel", "extra"}
        logging_kwargs: Dict[str, Any] = {}
        for key in list(kwargs.keys()):
            if key in reserved_keys:
                logging_kwargs[key] = kwargs.pop(key)

        structured_fields: Dict[str, Any] = kwargs  # whatever remains

        # Normalize/merge `extra`
        extra_obj = logging_kwargs.get("extra")
        extra_dict: Dict[str, Any] = {}
        if extra_obj is not None:
            if isinstance(extra_obj, dict):
                extra_dict = cast(Dict[str, Any], extra_obj)
            else:
                # Preserve unexpected `extra` content under a namespaced key
                extra_dict = {"original_extra": extra_obj}

        # Extract any free-form keys on `extra` (excluding nested extra_fields)
        extra_free_form: Dict[str, Any] = {}
        if extra_dict:
            extra_free_form = {k: v for k, v in extra_dict.items() if k != "extra_fields"}

        # Merge fields in order of increasing precedence
        # 1) existing extra.extra_fields, 2) extra free-form keys, 3) structured fields (kwargs)
        existing_fields = extra_dict.get("extra_fields")
        if isinstance(existing_fields, dict):
            merged_extra_fields = {**existing_fields, **extra_free_form, **structured_fields}
        else:
            merged_extra_fields = {**extra_free_form, **structured_fields}

        # Only attach `extra` if we have content to add
        if extra_dict or merged_extra_fields:
            extra_dict = {**extra_dict, "extra_fields": merged_extra_fields}
            logging_kwargs["extra"] = extra_dict

        # Delegate to underlying logger
        self.logger.log(level, message, *args, **logging_kwargs)

    @contextmanager
    def operation(
        self,
        operation_name: str,
        *args: Any,
        **context: Any,
    ) -> Generator[None, None, None]:
        """Context manager for tracking operations with metrics.
        Accepts additional positional args and keyword context for compatibility. Any extra
        kwargs will be treated as structured fields unless they collide with reserved
        logging kwargs (exc_info, stack_info, stacklevel, extra).

        Example:
            with logger.operation("fetch_user", request_id=req.id, user_id=uid):
                ...
        """
        start_time = time.perf_counter()
        self.info(
            f"🚀 Operation started: {operation_name}",
            *args,
            **context,
        )
        success = False
        try:
            yield
            success = True
        except Exception:
            # Log exception with traceback; reserved kwargs handled in _log
            self.exception(
                f"❌ Operation failed with exception: {operation_name}",
                *args,
                **context,
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            # Attach duration_ms as structured field while preserving original context
            if success:
                self.info(
                    f"✅ Operation completed: {operation_name}",
                    *args,
                    duration_ms=duration_ms,
                    **context,
                )
            else:
                self.error(
                    f"💥 Operation failed: {operation_name}",
                    *args,
                    duration_ms=duration_ms,
                    **context,
                )

    def log_request(self, method: str, endpoint: str, *args: Any, **kwargs: Any) -> None:
        """Log HTTP request. Additional args/kwargs are forwarded for compatibility."""
        self.info(
            f"📨 {method} {endpoint}",
            *args,
            method=method,
            endpoint=endpoint,
            **kwargs,
        )

    def log_response(self, status_code: int, duration_ms: float, *args: Any, **kwargs: Any) -> None:
        """Log HTTP response. Additional args/kwargs are forwarded for compatibility."""
        level = logging.INFO if status_code < 400 else logging.ERROR
        icon = "✅" if status_code < 400 else "❌"
        self._log(
            level,
            f"{icon} Response {status_code}",
            *args,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs,
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        if self.enable_metrics and self.metrics is not None:
            return self.metrics.get_metrics_summary()
        return {"metrics_disabled": True}

    def set_console_level(self, level: int) -> None:
        """Set console logging level"""
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(level)
                break


# Global logger registry
_loggers: Dict[str, "UnifiedLogger"] = {}
_lock = threading.Lock()


def get_unified_logger(
    name: str,
    log_file: Optional[str] = None,
    enable_json_logging: bool = True,
    enable_metrics: bool = True,
) -> "UnifiedLogger":
    """Get or create a unified logger instance"""
    with _lock:
        if name not in _loggers:
            if log_file is None:
                log_file = f"{name.lower().replace('.', '_')}.log"
            _loggers[name] = UnifiedLogger(name, log_file, enable_json_logging, enable_metrics)
        return _loggers[name]


# Backward compatibility functions


def get_logger(name: str) -> "UnifiedLogger":
    """Backward compatible logger getter"""
    return get_unified_logger(name)


def setup_logger(name: str, log_file: Optional[str] = None) -> "UnifiedLogger":
    """Backward compatible logger setup"""
    return get_unified_logger(name, log_file)


# Global system logger
system_logger = get_unified_logger("SYSTEM", "system.log")
logger = system_logger  # Alias for main.py compatibility

# Test function
if __name__ == "__main__":
    print("🧪 Testing unified logger...")

    test_logger = get_unified_logger("TEST")

    # Test basic logging
    test_logger.info("Testing unified logging", user_id="test_user", session_id="abc123")
    test_logger.warning("This is a warning", component="test")
    test_logger.error("This is an error", error_code=500)

    # Test operation tracking
    with test_logger.operation("test_operation", user="test"):
        time.sleep(0.1)  # Simulate work
        test_logger.info("Work in progress")

    # Test error handling
    try:
        with test_logger.operation("failing_operation"):
            raise ValueError("Test error")
    except ValueError:
        pass

    # Test metrics
    if test_logger.enable_metrics:
        metrics = test_logger.get_metrics_summary()
        print(f"📊 Metrics: {json.dumps(metrics, indent=2)}")

    print("✅ Unified logger test completed")
