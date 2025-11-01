"""Performance tracing utilities for latency measurement and bottleneck identification.

This module provides a lightweight tracing system to measure end-to-end latency
and identify performance bottlenecks in the chat pipeline.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

# Get logger for tracing
logger = logging.getLogger("TRACING")


@dataclass
class SpanData:
    """Data structure for a single span measurement."""

    name: str
    start_time: float
    end_time: float
    duration_ms: float
    thread_id: int
    parent_span: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for JSON serialization."""
        return {
            "timestamp": self.start_time,
            "span_name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "thread_id": self.thread_id,
            "parent_span": self.parent_span,
            "metadata": self.metadata or {},
        }


class PerformanceTracer:
    """Thread-safe performance tracer for measuring latency and bottlenecks."""

    def __init__(self, enabled: bool = True, log_file: Optional[str] = None):
        self.enabled = enabled
        self.log_file = log_file
        self._spans: Dict[int, List[SpanData]] = {}
        self._active_spans: Dict[int, List[str]] = {}
        self._lock = threading.Lock()

        # Setup file logging if specified
        if self.log_file:
            self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup file logging for trace data."""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler for trace logs
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)

        trace_logger = logging.getLogger("TRACE_DATA")
        trace_logger.setLevel(logging.INFO)
        trace_logger.addHandler(file_handler)
        trace_logger.propagate = False

    @contextmanager
    def span(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for measuring span duration.

        Args:
            name: Name of the span (e.g., 'llm_total', 'rag_embed')
            metadata: Optional metadata to include with the span

        Yields:
            SpanData object that can be used to add metadata during execution
        """
        if not self.enabled:
            yield None
            return

        thread_id = threading.get_ident()
        start_time = time.perf_counter()

        # Determine parent span
        parent_span = None
        with self._lock:
            if thread_id in self._active_spans and self._active_spans[thread_id]:
                parent_span = self._active_spans[thread_id][-1]

            # Add to active spans
            if thread_id not in self._active_spans:
                self._active_spans[thread_id] = []
            self._active_spans[thread_id].append(name)

        span_data = SpanData(
            name=name,
            start_time=start_time,
            end_time=0,
            duration_ms=0,
            thread_id=thread_id,
            parent_span=parent_span,
            metadata=metadata or {},
        )

        try:
            yield span_data
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            # Update span data
            span_data.end_time = end_time
            span_data.duration_ms = duration_ms

            with self._lock:
                # Remove from active spans
                if thread_id in self._active_spans:
                    self._active_spans[thread_id].pop()

                # Store completed span
                if thread_id not in self._spans:
                    self._spans[thread_id] = []
                self._spans[thread_id].append(span_data)

            # Log the span
            self._log_span(span_data)

    def _log_span(self, span: SpanData):
        """Log span data to structured logger and file."""
        span_dict = span.to_dict()

        # Log to main logger
        logger.info(
            f"📊 Span completed: {span.name}",
            duration_ms=span.duration_ms,
            parent=span.parent_span,
            thread_id=span.thread_id,
        )

        # Log to trace file if configured
        if self.log_file:
            trace_logger = logging.getLogger("TRACE_DATA")
            trace_logger.info(json.dumps(span_dict))

    def get_spans(self, thread_id: Optional[int] = None) -> List[SpanData]:
        """Get all spans for a specific thread or all threads."""
        with self._lock:
            if thread_id is not None:
                return self._spans.get(thread_id, []).copy()

            all_spans = []
            for spans in self._spans.values():
                all_spans.extend(spans)
            return all_spans

    def get_summary(self, span_name_filter: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary statistics."""
        spans = self.get_spans()

        if span_name_filter:
            spans = [s for s in spans if span_name_filter in s.name]

        if not spans:
            return {"total_spans": 0}

        durations = [s.duration_ms for s in spans]
        durations.sort()

        return {
            "total_spans": len(spans),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "p50_duration_ms": durations[len(durations) // 2],
            "p95_duration_ms": durations[int(len(durations) * 0.95)],
            "p99_duration_ms": durations[int(len(durations) * 0.99)],
        }

    def get_last_span_duration(
        self, span_name: str, thread_id: Optional[int] = None
    ) -> Optional[float]:
        """Get the duration of the most recent span with the given name.

        Args:
            span_name: Name of the span to find
            thread_id: Thread ID to search in (defaults to current thread)

        Returns:
            Duration in milliseconds, or None if span not found
        """
        if thread_id is None:
            thread_id = threading.get_ident()

        with self._lock:
            spans = self._spans.get(thread_id, [])

            # Search backwards for the most recent span with this name
            for span in reversed(spans):
                if span.name == span_name:
                    return span.duration_ms

        return None

    def clear_spans(self, thread_id: Optional[int] = None):
        """Clear stored spans for a specific thread or all threads."""
        with self._lock:
            if thread_id is not None:
                self._spans.pop(thread_id, None)
                self._active_spans.pop(thread_id, None)
            else:
                self._spans.clear()
                self._active_spans.clear()

    def export_spans_csv(self, filename: str, thread_id: Optional[int] = None):
        """Export spans to CSV format for analysis."""
        spans = self.get_spans(thread_id)

        if not spans:
            logger.warning("No spans to export")
            return

        import csv

        with open(filename, "w", newline="") as csvfile:
            fieldnames = ["timestamp", "span_name", "duration_ms", "thread_id", "parent_span"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for span in spans:
                writer.writerow(
                    {
                        "timestamp": span.start_time,
                        "span_name": span.name,
                        "duration_ms": span.duration_ms,
                        "thread_id": span.thread_id,
                        "parent_span": span.parent_span or "",
                    }
                )

        logger.info(f"📊 Exported {len(spans)} spans to {filename}")


# Global tracer instance
_global_tracer: Optional[PerformanceTracer] = None


def get_tracer() -> PerformanceTracer:
    """Get the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        # Import config here to avoid circular imports
        try:
            from src.backend.utils.unified_config import get_config

            config = get_config()
            enabled = config.system.trace_enabled
            log_file = str(config.paths.logs_dir / "trace_data.jsonl")
        except ImportError:
            enabled = True
            log_file = "logs/trace_data.jsonl"

        _global_tracer = PerformanceTracer(enabled=enabled, log_file=log_file)

    return _global_tracer


def span(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Convenience function to create a span using the global tracer."""
    return get_tracer().span(name, metadata)


def clear_traces():
    """Clear all stored traces."""
    get_tracer().clear_spans()


def get_trace_summary(span_filter: Optional[str] = None) -> Dict[str, Any]:
    """Get trace summary using the global tracer."""
    return get_tracer().get_summary(span_filter)


def export_traces_csv(filename: str):
    """Export traces to CSV using the global tracer."""
    get_tracer().export_spans_csv(filename)


def get_last_span_duration(span_name: str) -> Optional[float]:
    """Get the duration of the most recent span with the given name."""
    return get_tracer().get_last_span_duration(span_name)
