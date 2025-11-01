#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured Logging Module for LeonelResponde Assistant

This module provides enhanced logging capabilities with:
- Structured JSON logging
- Performance metrics tracking
- Request/response logging
- Error tracking with context
- Resource usage monitoring

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
from typing import Any, Dict, Optional

# Third-party imports
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


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


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add custom fields from extra
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """Enhanced colored formatter for console output"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
    }

    ICONS = {
        "DEBUG": "🔍",
        "INFO": "📝",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.WHITE)
        icon = self.ICONS.get(record.levelname, "📋")

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        # Format components
        level_colored = f"{log_color}{record.levelname:<8}{Style.RESET_ALL}"
        name_colored = f"{Fore.BLUE}{record.name:<12}{Style.RESET_ALL}"

        # Add performance metrics if available
        metrics_info = ""
        if hasattr(record, "duration_ms"):
            metrics_info = f" [{record.duration_ms:.2f}ms]"
        if hasattr(record, "memory_mb"):
            metrics_info += f" [RAM: {record.memory_mb:.1f}MB]"

        # Wrap long line to satisfy E501 while keeping readability
        formatted_message = (
            f"{icon} {timestamp} | {level_colored} | {name_colored} | "
            f"{record.getMessage()}{metrics_info}"
        )

        # Add exception info if present
        if record.exc_info:
            formatted_message += f"\n{Fore.RED}Exception: {record.exc_info[1]}{Style.RESET_ALL}"

        return formatted_message


class MetricsTracker:
    """Thread-safe metrics tracking"""

    def __init__(self):
        self._metrics = []
        self._lock = threading.Lock()
        self._operation_start_times = {}

    def start_operation(self, operation_id: str, operation_name: str):
        """Start tracking an operation"""
        with self._lock:
            self._operation_start_times[operation_id] = {
                "name": operation_name,
                "start_time": time.time(),
            }

    def end_operation(
        self, operation_id: str, success: bool = True, context: Optional[Dict[str, Any]] = None
    ) -> Optional[LogMetrics]:
        """End tracking an operation and return metrics"""
        with self._lock:
            if operation_id not in self._operation_start_times:
                return None

            start_info = self._operation_start_times.pop(operation_id)
            duration_ms = (time.time() - start_info["start_time"]) * 1000

            metrics = LogMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                operation=start_info["name"],
                duration_ms=duration_ms,
                success=success,
                context=context or {},
            )

            self._metrics.append(metrics)
            return metrics

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked metrics"""
        with self._lock:
            if not self._metrics:
                return {"total_operations": 0}

            total_ops = len(self._metrics)
            successful_ops = sum(1 for m in self._metrics if m.success)
            avg_duration = sum(m.duration_ms for m in self._metrics) / total_ops

            return {
                "total_operations": total_ops,
                "successful_operations": successful_ops,
                "success_rate": successful_ops / total_ops * 100,
                "average_duration_ms": avg_duration,
                "operations_by_type": self._group_by_operation(),
            }

    def _group_by_operation(self) -> Dict[str, Dict[str, Any]]:
        """Group metrics by operation type"""
        grouped = {}
        for metric in self._metrics:
            op_name = metric.operation
            if op_name not in grouped:
                grouped[op_name] = {"count": 0, "total_duration_ms": 0, "success_count": 0}

            grouped[op_name]["count"] += 1
            grouped[op_name]["total_duration_ms"] += metric.duration_ms
            if metric.success:
                grouped[op_name]["success_count"] += 1

        # Calculate averages
        for op_data in grouped.values():
            op_data["average_duration_ms"] = op_data["total_duration_ms"] / op_data["count"]
            op_data["success_rate"] = op_data["success_count"] / op_data["count"] * 100

        return grouped


class StructuredLogger:
    """Enhanced logger with structured logging and metrics"""

    def __init__(self, name: str, log_file: Optional[str] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.metrics_tracker = MetricsTracker()

        # Avoid duplicate handlers
        if self.logger.handlers:
            return

        self._setup_handlers(log_file)

    def _setup_handlers(self, log_file: Optional[str]):
        """Setup console and file handlers"""
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredConsoleFormatter()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with JSON structured logs
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            json_formatter = StructuredFormatter()
            file_handler.setFormatter(json_formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs):
        extra = {"extra_fields": {k: v for k, v in kwargs.items() if k not in {"exc_info"}}}

        # Support performance metrics fields
        if "duration_ms" in kwargs:
            extra["duration_ms"] = kwargs["duration_ms"]
        if "memory_mb" in kwargs:
            extra["memory_mb"] = kwargs["memory_mb"]

        self.logger.log(level, message, extra=extra, exc_info=kwargs.get("exc_info"))

    @contextmanager
    def operation(self, operation_name: str, **context):
        """Context manager for logging an operation with timing"""
        op_id = f"{operation_name}-{int(time.time() * 1000)}"
        self.metrics_tracker.start_operation(op_id, operation_name)
        start_time = time.time()
        try:
            yield
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Operation '{operation_name}' completed",
                duration_ms=duration_ms,
                **context,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.error(
                f"Operation '{operation_name}' failed: {e}",
                duration_ms=duration_ms,
                exc_info=True,
                **context,
            )
            raise
        finally:
            self.metrics_tracker.end_operation(
                op_id,
                success=("e" not in locals()),
                context=context,
            )

    def log_request(self, method: str, endpoint: str, **kwargs):
        self.info(f"Request: {method} {endpoint}", **kwargs)

    def log_response(self, status_code: int, duration_ms: float, **kwargs):
        self.info(f"Response: {status_code}", duration_ms=duration_ms, **kwargs)

    def get_metrics_summary(self) -> Dict[str, Any]:
        return self.metrics_tracker.get_metrics_summary()

    def set_console_level(self, level: int):
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)


_loggers = {}


def get_structured_logger(name: str) -> StructuredLogger:
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


def get_logger(name: str) -> StructuredLogger:
    return get_structured_logger(name)


system_logger = get_structured_logger("SYSTEM")


if __name__ == "__main__":
    print("🧪 Testing structured logger...")

    test_logger = get_structured_logger("TEST")

    # Basic logging
    test_logger.info("Testing structured logging", user_id="test_user", session_id="abc123")

    # Timing context manager
    with test_logger.operation("test_operation", user="test"):
        time.sleep(0.1)  # Simulate work
        test_logger.info("Work in progress")

    # Exception handling
    try:
        with test_logger.operation("failing_operation"):
            raise ValueError("Test error")
    except ValueError:
        pass

    metrics = test_logger.get_metrics_summary()
    print(f"📊 Metrics: {json.dumps(metrics, indent=2)}")

    print("✅ Structured logger test completed")
