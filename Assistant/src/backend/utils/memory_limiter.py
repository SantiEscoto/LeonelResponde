# Standard library imports
from dataclasses import dataclass
import gc
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional

# Third-party imports
try:
    import psutil
except ImportError:
    psutil = None

# Local imports
from pathlib import Path
current_file = Path(__file__)
project_root = current_file.parent.parent.parent
sys.path.append(str(project_root))

try:
    from src.backend.utils.unified_logger import get_unified_logger
except ImportError:
    import logging

    def get_structured_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)


try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("MemoryLimiter")
except ImportError:
    import logging
    logger = logging.getLogger("MemoryLimiter")


@dataclass
class MemoryLimits:
    """Configuration for memory limits"""

    max_memory_mb: int = 2048  # Maximum memory usage in MB
    max_cache_size_mb: int = 512  # Maximum cache size in MB
    cleanup_threshold: float = 0.85  # Cleanup when reaching 85% of limit
    emergency_threshold: float = 0.95  # Emergency cleanup at 95%
    check_interval: float = 30.0  # Check every 30 seconds


class MemoryLimiter:
    """
    Memory management system with automatic cleanup and limits
    Monitors memory usage and performs cleanup when thresholds are exceeded
    """

    def __init__(self, limits: Optional[MemoryLimits] = None):
        """
        Initialize the memory limiter

        Args:
            limits: Memory limits configuration
        """
        self.limits = limits or MemoryLimits()
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.cleanup_callbacks: Dict[str, Callable] = {}
        self.cache_registry: Dict[str, Dict[str, Any]] = {}
        self.last_cleanup_time = 0
        self.cleanup_stats = {
            "total_cleanups": 0,
            "memory_freed_mb": 0,
            "last_cleanup_reason": None,
        }

        logger.info(f"🔧 MemoryLimiter initialized with {self.limits.max_memory_mb}MB limit")

    def register_cleanup_callback(self, name: str, callback: Callable) -> None:
        """
        Register a cleanup callback function

        Args:
            name: Name of the callback
            callback: Function to call for cleanup
        """
        self.cleanup_callbacks[name] = callback
        logger.info(f"📝 Cleanup callback registered: {name}")

    def register_cache(self, name: str, cache_info: Dict[str, Any]) -> None:
        """
        Register a cache for monitoring

        Args:
            name: Name of the cache
            cache_info: Dictionary with cache information (size_func, clear_func, etc.)
        """
        self.cache_registry[name] = cache_info
        logger.info(f"📦 Cache registered: {name}")

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage information

        Returns:
            Dictionary with memory usage statistics
        """
        if not psutil:
            return {"error": "psutil not available"}

        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {"error": str(e)}

    def get_cache_sizes(self) -> Dict[str, float]:
        """
        Get sizes of registered caches

        Returns:
            Dictionary with cache sizes in MB
        """
        cache_sizes = {}

        for name, cache_info in self.cache_registry.items():
            try:
                if "size_func" in cache_info:
                    size_bytes = cache_info["size_func"]()
                    cache_sizes[name] = size_bytes / 1024 / 1024  # Convert to MB
                else:
                    cache_sizes[name] = 0
            except Exception as e:
                logger.error(f"Error getting size for cache {name}: {e}")
                cache_sizes[name] = -1  # Error indicator

        return cache_sizes

    def should_cleanup(self, memory_usage: Dict[str, float]) -> tuple[bool, str]:
        """
        Determine if cleanup is needed

        Args:
            memory_usage: Current memory usage information

        Returns:
            Tuple of (should_cleanup, reason)
        """
        if "rss_mb" not in memory_usage:
            return False, "No memory info available"

        current_mb = memory_usage["rss_mb"]

        # Emergency cleanup
        if current_mb >= self.limits.max_memory_mb * self.limits.emergency_threshold:
            msg = (
                "Emergency: "
                f"{current_mb:.1f}MB >= "
                f"{self.limits.max_memory_mb * self.limits.emergency_threshold:.1f}MB"
            )
            return True, msg

        # Regular cleanup
        if current_mb >= self.limits.max_memory_mb * self.limits.cleanup_threshold:
            msg = (
                "Threshold: "
                f"{current_mb:.1f}MB >= "
                f"{self.limits.max_memory_mb * self.limits.cleanup_threshold:.1f}MB"
            )
            return True, msg

        # Cache size check
        cache_sizes = self.get_cache_sizes()
        total_cache_mb = sum(size for size in cache_sizes.values() if size > 0)

        if total_cache_mb >= self.limits.max_cache_size_mb:
            return True, f"Cache limit: {total_cache_mb:.1f}MB >= {self.limits.max_cache_size_mb}MB"

        return False, "No cleanup needed"

    def perform_cleanup(self, reason: str = "Manual") -> Dict[str, Any]:
        """
        Perform memory cleanup

        Args:
            reason: Reason for cleanup

        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"🧹 Starting memory cleanup: {reason}")

        memory_before = self.get_memory_usage()
        cleanup_results = {
            "reason": reason,
            "memory_before_mb": memory_before.get("rss_mb", 0),
            "caches_cleared": [],
            "callbacks_executed": [],
            "errors": [],
        }

        # Clear registered caches
        for name, cache_info in self.cache_registry.items():
            try:
                if "clear_func" in cache_info:
                    cache_info["clear_func"]()
                    cleanup_results["caches_cleared"].append(name)
                    logger.info(f"🗑️ Cache cleared: {name}")
            except Exception as e:
                error_msg = f"Error clearing cache {name}: {e}"
                logger.error(error_msg)
                cleanup_results["errors"].append(error_msg)

        # Execute cleanup callbacks
        for name, callback in self.cleanup_callbacks.items():
            try:
                callback()
                cleanup_results["callbacks_executed"].append(name)
                logger.info(f"🔧 Cleanup callback executed: {name}")
            except Exception as e:
                error_msg = f"Error executing cleanup callback {name}: {e}"
                logger.error(error_msg)
                cleanup_results["errors"].append(error_msg)

        # Force garbage collection
        gc.collect()

        # Get memory usage after cleanup
        memory_after = self.get_memory_usage()
        cleanup_results["memory_after_mb"] = memory_after.get("rss_mb", 0)
        cleanup_results["memory_freed_mb"] = (
            cleanup_results["memory_before_mb"] - cleanup_results["memory_after_mb"]
        )

        # Update stats
        self.cleanup_stats["total_cleanups"] += 1
        self.cleanup_stats["memory_freed_mb"] += cleanup_results["memory_freed_mb"]
        self.cleanup_stats["last_cleanup_reason"] = reason
        self.last_cleanup_time = time.time()

        logger.info(f"✅ Cleanup completed: {cleanup_results['memory_freed_mb']:.1f}MB freed")

        return cleanup_results

    def start_monitoring(self) -> None:
        """
        Start automatic memory monitoring
        """
        if self.is_monitoring:
            logger.warning("⚠️ Memory monitoring already running")
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info(f"🔄 Memory monitoring started (interval: {self.limits.check_interval}s)")

    def stop_monitoring(self) -> None:
        """
        Stop automatic memory monitoring
        """
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("⏹️ Memory monitoring stopped")

    def _monitor_loop(self) -> None:
        """
        Main monitoring loop (runs in separate thread)
        """
        while self.is_monitoring:
            try:
                memory_usage = self.get_memory_usage()

                if "rss_mb" in memory_usage:
                    should_cleanup, reason = self.should_cleanup(memory_usage)

                    if should_cleanup:
                        # Avoid too frequent cleanups
                        time_since_last = time.time() - self.last_cleanup_time
                        if time_since_last >= 60:  # At least 1 minute between cleanups
                            self.perform_cleanup(reason)
                        else:
                            logger.debug(
                                f"⏳ Cleanup skipped (too recent): {time_since_last:.1f}s ago"
                            )

                time.sleep(self.limits.check_interval)

            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                time.sleep(self.limits.check_interval)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of memory limiter

        Returns:
            Dictionary with status information
        """
        memory_usage = self.get_memory_usage()
        cache_sizes = self.get_cache_sizes()

        return {
            "is_monitoring": self.is_monitoring,
            "limits": {
                "max_memory_mb": self.limits.max_memory_mb,
                "max_cache_size_mb": self.limits.max_cache_size_mb,
                "cleanup_threshold": self.limits.cleanup_threshold,
                "emergency_threshold": self.limits.emergency_threshold,
            },
            "current_usage": memory_usage,
            "cache_sizes": cache_sizes,
            "total_cache_mb": sum(size for size in cache_sizes.values() if size > 0),
            "registered_caches": list(self.cache_registry.keys()),
            "registered_callbacks": list(self.cleanup_callbacks.keys()),
            "cleanup_stats": self.cleanup_stats.copy(),
            "time_since_last_cleanup": (
                time.time() - self.last_cleanup_time if self.last_cleanup_time > 0 else None
            ),
        }


# Global memory limiter instance
_global_memory_limiter: Optional[MemoryLimiter] = None


def get_memory_limiter(limits: Optional[MemoryLimits] = None) -> MemoryLimiter:
    """
    Get or create the global memory limiter instance

    Args:
        limits: Memory limits configuration (only used on first call)

    Returns:
        Global MemoryLimiter instance
    """
    global _global_memory_limiter

    if _global_memory_limiter is None:
        _global_memory_limiter = MemoryLimiter(limits)

    return _global_memory_limiter


def start_global_memory_monitoring(limits: Optional[MemoryLimits] = None) -> MemoryLimiter:
    """
    Start global memory monitoring

    Args:
        limits: Memory limits configuration

    Returns:
        Global MemoryLimiter instance
    """
    limiter = get_memory_limiter(limits)
    limiter.start_monitoring()
    return limiter


# Test functionality
if __name__ == "__main__":
    print("🧪 Testing MemoryLimiter...")

    # Create test limiter
    test_limits = MemoryLimits(max_memory_mb=1024, check_interval=5.0)
    limiter = MemoryLimiter(test_limits)

    # Test memory usage
    usage = limiter.get_memory_usage()
    print(f"📊 Current memory usage: {usage}")

    # Test cleanup
    result = limiter.perform_cleanup("Test")
    print(f"🧹 Cleanup result: {result}")

    # Test status
    status = limiter.get_status()
    print(f"📋 Status: {status}")

    print("✅ MemoryLimiter test completed")
