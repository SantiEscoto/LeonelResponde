#!/usr/bin/env python3
"""
Resource Monitor Module

Provides real-time monitoring of system resources including CPU, RAM, and GPU usage.
Designed for offline AI assistant to track resource consumption and prevent overload.

Author: Assistant
Date: 2024
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
import threading
import time
from typing import Callable, Dict, List, Optional

import psutil

try:
    import GPUtil

    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Add MPS/Metal detection imports
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import platform

    PLATFORM_AVAILABLE = True
except ImportError:
    PLATFORM_AVAILABLE = False

from .unified_logger import get_unified_logger

logger = get_unified_logger(__name__)


@dataclass
class ResourceSnapshot:
    """Represents a snapshot of system resources at a specific time."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    gpu_usage: Optional[List[Dict]] = None
    process_count: int = 0

    def to_dict(self) -> Dict:
        """Convert snapshot to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_percent": self.disk_usage_percent,
            "gpu_usage": self.gpu_usage,
            "process_count": self.process_count,
        }


class ResourceMonitor:
    """Real-time system resource monitor with alerting capabilities."""

    def __init__(
        self,
        monitoring_interval: float = 5.0,
        history_size: int = 100,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        gpu_threshold: float = 90.0,
        alerts_enabled: bool = False,
    ):
        """
        Initialize resource monitor.

        Args:
            monitoring_interval: Seconds between resource checks
            history_size: Number of snapshots to keep in memory
            cpu_threshold: CPU usage percentage to trigger alerts
            memory_threshold: Memory usage percentage to trigger alerts
            gpu_threshold: GPU usage percentage to trigger alerts
        """
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.gpu_threshold = gpu_threshold
        self.alerts_enabled = alerts_enabled

        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._history: List[ResourceSnapshot] = []
        self._lock = threading.Lock()
        self._alert_callbacks: List[Callable[[str, ResourceSnapshot], None]] = []

        # Configure logger to not print warnings to console to avoid interfering with chat
        logger.set_console_level(logging.ERROR)

        logger.info(f"🔧 ResourceMonitor initialized with {monitoring_interval}s interval")

    def add_alert_callback(self, callback: Callable[[str, ResourceSnapshot], None]):
        """Add a callback function to be called when resource alerts are triggered."""
        self._alert_callbacks.append(callback)

    def enable_alerts(self):
        """Enable resource alerts."""
        self.alerts_enabled = True
        logger.info("🔔 Resource alerts enabled")

    def disable_alerts(self):
        """Disable resource alerts."""
        self.alerts_enabled = False
        logger.info("🔕 Resource alerts disabled")

    def toggle_alerts(self, enabled: bool = None):
        """Toggle resource alerts on/off. If enabled is None, toggles current state."""
        if enabled is None:
            self.alerts_enabled = not self.alerts_enabled
        else:
            self.alerts_enabled = enabled

        status = "enabled" if self.alerts_enabled else "disabled"
        logger.info(f"🔔 Resource alerts {status}")
        logger.info("📢 Alert callback registered")

    def get_current_snapshot(self) -> ResourceSnapshot:
        """Get current system resource snapshot."""
        # CPU usage (removed excessive logging)
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)

        # Disk usage (root partition)
        disk = psutil.disk_usage("/")
        disk_usage_percent = (disk.used / disk.total) * 100

        # Process count
        process_count = len(psutil.pids())

        # GPU usage (if available)
        gpu_usage = None
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                gpu_usage = []
                for gpu in gpus:
                    gpu_usage.append(
                        {
                            "id": gpu.id,
                            "name": gpu.name,
                            "load": gpu.load * 100,
                            "memory_used": gpu.memoryUsed,
                            "memory_total": gpu.memoryTotal,
                            "memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                            "temperature": gpu.temperature,
                        }
                    )
            except Exception as e:
                logger.warning(f"⚠️ Error reading GPU info: {e}")

        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_usage_percent=disk_usage_percent,
            gpu_usage=gpu_usage,
            process_count=process_count,
        )

        # Only log detailed info when thresholds are exceeded or every 10th snapshot
        # Commented out to prevent console spam during user interactions
        # if (cpu_percent > self.cpu_threshold or
        #     memory_percent > self.memory_threshold or
        #     len(self._history) % 10 == 0):
        #     logger.info(
        #         f"📊 Resource snapshot: CPU {cpu_percent:.1f}%, "
        #         f"RAM {memory_percent:.1f}%, Processes {process_count}"
        #     )

        return snapshot

    def _check_thresholds(self, snapshot: ResourceSnapshot):
        """Check if any resource thresholds are exceeded and trigger alerts."""
        alerts = []

        # CPU threshold
        if snapshot.cpu_percent > self.cpu_threshold:
            alerts.append(f"CPU usage high: {snapshot.cpu_percent:.1f}%")

        # Memory threshold
        if snapshot.memory_percent > self.memory_threshold:
            alerts.append(f"Memory usage high: {snapshot.memory_percent:.1f}%")

        # GPU threshold
        if snapshot.gpu_usage:
            for gpu in snapshot.gpu_usage:
                if gpu["load"] > self.gpu_threshold:
                    alerts.append(f"GPU {gpu['id']} usage high: {gpu['load']:.1f}%")
                if gpu["memory_percent"] > self.gpu_threshold:
                    alerts.append(f"GPU {gpu['id']} memory high: {gpu['memory_percent']:.1f}%")

        # Trigger alerts only if enabled
        if self.alerts_enabled and alerts:
            for alert_msg in alerts:
                logger.warning(f"🚨 Resource Alert: {alert_msg}")
                for callback in self._alert_callbacks:
                    try:
                        callback(alert_msg, snapshot)
                    except Exception as e:
                        logger.error(f"❌ Error in alert callback: {e}")

    def _monitor_loop(self):
        """Main monitoring loop running in separate thread."""
        logger.info("🔄 Resource monitoring started")

        while self._monitoring:
            try:
                snapshot = self.get_current_snapshot()

                # Add to history
                with self._lock:
                    self._history.append(snapshot)
                    if len(self._history) > self.history_size:
                        self._history.pop(0)

                # Check thresholds
                self._check_thresholds(snapshot)

                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def start_monitoring(self):
        """Start continuous resource monitoring in background thread."""
        if self._monitoring:
            logger.warning("⚠️ Monitoring already running")
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("✅ Resource monitoring started")

    def stop_monitoring(self):
        """Stop continuous resource monitoring."""
        if not self._monitoring:
            logger.warning("⚠️ Monitoring not running")
            return

        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("🛑 Resource monitoring stopped")

    def get_history(self, last_n: Optional[int] = None) -> List[ResourceSnapshot]:
        """Get resource history snapshots."""
        with self._lock:
            history = self._history.copy()
            if last_n:
                history = history[-last_n:]
            return history

    def get_average_usage(self, last_n: Optional[int] = None) -> Dict[str, float]:
        """Get average resource usage over specified number of snapshots."""
        history = self.get_history(last_n)

        if not history:
            return {}

        total_snapshots = len(history)
        avg_cpu = sum(s.cpu_percent for s in history) / total_snapshots
        avg_memory = sum(s.memory_percent for s in history) / total_snapshots
        avg_disk = sum(s.disk_usage_percent for s in history) / total_snapshots

        result = {
            "cpu_percent": avg_cpu,
            "memory_percent": avg_memory,
            "disk_usage_percent": avg_disk,
            "snapshots_count": total_snapshots,
        }

        # GPU averages if available
        gpu_snapshots = [s for s in history if s.gpu_usage]
        if gpu_snapshots:
            gpu_count = len(gpu_snapshots[0].gpu_usage) if gpu_snapshots[0].gpu_usage else 0
            for gpu_id in range(gpu_count):
                gpu_loads = [
                    s.gpu_usage[gpu_id]["load"] for s in gpu_snapshots if len(s.gpu_usage) > gpu_id
                ]
                gpu_memory = [
                    s.gpu_usage[gpu_id]["memory_percent"]
                    for s in gpu_snapshots
                    if len(s.gpu_usage) > gpu_id
                ]

                if gpu_loads:
                    result[f"gpu_{gpu_id}_load"] = sum(gpu_loads) / len(gpu_loads)
                    result[f"gpu_{gpu_id}_memory"] = sum(gpu_memory) / len(gpu_memory)

        return result

    def export_history(self, filepath: str):
        """Export resource history to JSON file."""
        history = self.get_history()
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "monitoring_config": {
                "interval": self.monitoring_interval,
                "cpu_threshold": self.cpu_threshold,
                "memory_threshold": self.memory_threshold,
                "gpu_threshold": self.gpu_threshold,
            },
            "snapshots": [s.to_dict() for s in history],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"📁 Resource history exported to {filepath} ({len(history)} snapshots)")

    def get_system_info(self) -> Dict:
        """Get static system information."""
        info = {
            "cpu_count": psutil.cpu_count(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "disk_total_gb": psutil.disk_usage("/").total / (1024**3),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "python_process_pid": os.getpid(),
        }

        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                info["gpu_count"] = len(gpus)
                info["gpus"] = [
                    {"id": gpu.id, "name": gpu.name, "memory_total": gpu.memoryTotal}
                    for gpu in gpus
                ]
            except Exception as e:
                info["gpu_error"] = str(e)
        else:
            info["gpu_available"] = False

        return info

    def get_enhanced_gpu_info(self) -> Dict:
        """Get enhanced GPU information including MPS/Metal support on macOS."""
        gpu_info = {
            "available": False,
            "type": "none",
            "devices": [],
            "mps_available": False,
            "metal_available": False,
            "torch_device": "cpu",
        }

        # Check for PyTorch MPS support (Apple Silicon)
        if TORCH_AVAILABLE:
            try:
                if hasattr(torch.backends, "mps"):
                    gpu_info["mps_available"] = torch.backends.mps.is_available()
                    if gpu_info["mps_available"]:
                        gpu_info["available"] = True
                        gpu_info["type"] = "mps"
                        gpu_info["torch_device"] = "mps"

                        # Get Metal GPU information on macOS
                        if PLATFORM_AVAILABLE and platform.system() == "Darwin":
                            gpu_info["metal_available"] = True
                            try:
                                # Try to get more detailed Metal info
                                import subprocess

                                result = subprocess.run(
                                    ["system_profiler", "SPDisplaysDataType"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5,
                                )
                                if result.returncode == 0:
                                    lines = result.stdout.split("\n")
                                    for line in lines:
                                        if "Chipset Model:" in line:
                                            chipset = line.split(":")[1].strip()
                                            gpu_info["devices"].append(
                                                {
                                                    "id": 0,
                                                    "name": chipset,
                                                    "type": "Apple Silicon",
                                                    "memory_unified": True,
                                                    "mps_enabled": True,
                                                }
                                            )
                                            break
                            except Exception as e:
                                logger.debug(f"Could not get detailed Metal info: {e}")
                                # Fallback to basic info
                                gpu_info["devices"].append(
                                    {
                                        "id": 0,
                                        "name": "Apple Silicon GPU",
                                        "type": "Apple Silicon",
                                        "memory_unified": True,
                                        "mps_enabled": True,
                                    }
                                )

                # Check for CUDA support
                if torch.cuda.is_available():
                    gpu_info["available"] = True
                    if gpu_info["type"] == "none":
                        gpu_info["type"] = "cuda"
                        gpu_info["torch_device"] = "cuda"

                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        gpu_info["devices"].append(
                            {
                                "id": i,
                                "name": props.name,
                                "type": "CUDA",
                                "memory_total": props.total_memory // (1024**2),  # MB
                                "compute_capability": f"{props.major}.{props.minor}",
                            }
                        )

            except Exception as e:
                logger.debug(f"Error checking PyTorch GPU support: {e}")

        # Check for traditional GPU via GPUtil (NVIDIA)
        if GPU_AVAILABLE and not gpu_info["available"]:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_info["available"] = True
                    gpu_info["type"] = "nvidia"
                    for gpu in gpus:
                        gpu_info["devices"].append(
                            {
                                "id": gpu.id,
                                "name": gpu.name,
                                "type": "NVIDIA",
                                "load": gpu.load * 100,
                                "memory_used": gpu.memoryUsed,
                                "memory_total": gpu.memoryTotal,
                                "memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                                "temperature": gpu.temperature,
                            }
                        )
            except Exception as e:
                logger.debug(f"Error checking NVIDIA GPU: {e}")

        return gpu_info


# Global monitor instance
_global_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor(**kwargs) -> ResourceMonitor:
    """Get global resource monitor instance (singleton pattern)."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ResourceMonitor(**kwargs)
    return _global_monitor


def start_global_monitoring(**kwargs):
    """Start global resource monitoring."""
    monitor = get_resource_monitor(**kwargs)
    monitor.start_monitoring()
    return monitor


def stop_global_monitoring():
    """Stop global resource monitoring."""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop_monitoring()


if __name__ == "__main__":
    # Test the resource monitor
    print("Testing Resource Monitor...")

    monitor = ResourceMonitor(monitoring_interval=2.0)

    # Add alert callback
    def alert_handler(message: str, snapshot: ResourceSnapshot):
        print(f"ALERT: {message}")

    monitor.add_alert_callback(alert_handler)

    # Get system info
    print("System Info:")
    print(json.dumps(monitor.get_system_info(), indent=2))

    # Get current snapshot
    print("\nCurrent Snapshot:")
    snapshot = monitor.get_current_snapshot()
    print(json.dumps(snapshot.to_dict(), indent=2))

    # Start monitoring for 10 seconds
    print("\nStarting monitoring for 10 seconds...")
    monitor.start_monitoring()
    time.sleep(10)
    monitor.stop_monitoring()

    # Show averages
    print("\nAverage Usage:")
    print(json.dumps(monitor.get_average_usage(), indent=2))

    print("\nTest completed!")
