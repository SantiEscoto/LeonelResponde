#!/usr/bin/env python3
"""
System Protection Module

Prevents kernel panics and system overload by implementing:
- Resource usage limits
- Emergency shutdown procedures
- System health monitoring
- Automatic resource cleanup

Author: Assistant
Date: 2024
"""

import gc
import logging
import os
import psutil
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable

from .unified_logger import get_unified_logger

logger = get_unified_logger(__name__)


@dataclass
class SystemLimits:
    """System resource limits to prevent overload"""
    
    max_cpu_percent: float = 80.0  # Maximum CPU usage
    max_memory_percent: float = 85.0  # Maximum memory usage
    max_memory_mb: int = 6000  # Maximum memory in MB
    max_process_count: int = 200  # Maximum number of processes
    max_file_descriptors: int = 1000  # Maximum file descriptors
    emergency_threshold: float = 98.0  # Emergency shutdown threshold (relaxed for dev)
    check_interval: float = 10.0  # Check interval in seconds (less frequent for dev)


@dataclass
class SystemHealth:
    """Current system health status"""
    
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    process_count: int
    file_descriptors: int
    load_average: List[float]
    is_healthy: bool
    warnings: List[str]


class SystemProtection:
    """
    System protection manager to prevent kernel panics
    """
    
    def __init__(self, limits: Optional[SystemLimits] = None):
        self.limits = limits or SystemLimits()
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.emergency_callbacks: List[Callable] = []
        self.warning_callbacks: List[Callable] = []
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=5)
        
        # Configure logger to not print warnings to console to avoid interfering with chat
        logger.set_console_level(logging.ERROR)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("🛡️ System Protection initialized")
    
    def start_monitoring(self):
        """Start system health monitoring"""
        if self.is_monitoring:
            logger.warning("⚠️ System monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="SystemProtection"
        )
        self.monitor_thread.start()
        logger.info("🔍 System monitoring started")
    
    def stop_monitoring(self):
        """Stop system health monitoring"""
        self.is_monitoring = False
        # Avoid joining from the same thread to prevent deadlock
        if (
            self.monitor_thread
            and self.monitor_thread.is_alive()
            and threading.current_thread() is not self.monitor_thread
        ):
            self.monitor_thread.join(timeout=5.0)
        logger.info("🛑 System monitoring stopped")
    
    def register_emergency_callback(self, callback: Callable):
        """Register callback for emergency situations"""
        self.emergency_callbacks.append(callback)
        logger.info(f"🚨 Emergency callback registered: {callback.__name__}")
    
    def register_warning_callback(self, callback: Callable):
        """Register callback for warning situations"""
        self.warning_callbacks.append(callback)
        logger.info(f"⚠️ Warning callback registered: {callback.__name__}")
    
    def get_system_health(self) -> SystemHealth:
        """Get current system health status"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # Process count
            process_count = len(psutil.pids())
            
            # File descriptors (if available)
            try:
                file_descriptors = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
            except (OSError, PermissionError):
                file_descriptors = 0
            
            # Load average
            try:
                load_average = list(os.getloadavg())
            except (OSError, AttributeError):
                load_average = [0.0, 0.0, 0.0]
            
            # Check health status
            warnings = []
            is_healthy = True
            
            if cpu_percent > self.limits.max_cpu_percent:
                warnings.append(f"High CPU usage: {cpu_percent:.1f}%")
                is_healthy = False
            
            if memory_percent > self.limits.max_memory_percent:
                warnings.append(f"High memory usage: {memory_percent:.1f}%")
                is_healthy = False
            
            if memory_used_mb > self.limits.max_memory_mb:
                warnings.append(f"High memory usage: {memory_used_mb:.1f}MB")
                is_healthy = False
            
            if process_count > self.limits.max_process_count:
                warnings.append(f"High process count: {process_count}")
                is_healthy = False
            
            if file_descriptors > self.limits.max_file_descriptors:
                warnings.append(f"High file descriptor count: {file_descriptors}")
                is_healthy = False
            
            return SystemHealth(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                process_count=process_count,
                file_descriptors=file_descriptors,
                load_average=load_average,
                is_healthy=is_healthy,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting system health: {e}")
            return SystemHealth(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                process_count=0,
                file_descriptors=0,
                load_average=[0.0, 0.0, 0.0],
                is_healthy=False,
                warnings=[f"Health check failed: {e}"]
            )
    
    def emergency_cleanup(self):
        """Perform emergency system cleanup"""
        logger.warning("🚨 EMERGENCY CLEANUP INITIATED")
        
        try:
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"🗑️ Garbage collection: {collected} objects collected")
            
            # Clear Python caches (safely)
            try:
                # Clear only non-essential modules to avoid breaking sys and torch
                essential_modules = {
                    'sys', 'os', 'builtins', '__main__', 
                    'torch', 'torch.cuda', 'torch.nn', 'torch.optim',
                    'transformers', 'sentence_transformers'
                }
                modules_to_clear = [name for name in list(sys.modules.keys()) 
                                  if name not in essential_modules and not name.startswith('torch')]
                for module_name in modules_to_clear:
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                logger.info(f"🧹 Python module cache cleared: {len(modules_to_clear)} modules")
            except Exception as clear_error:
                logger.warning(f"⚠️ Error clearing module cache: {clear_error}")
            
            # Clear GPU memory if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    logger.info("🎮 GPU memory cleared")
            except ImportError:
                pass
            
            # Call emergency callbacks
            for callback in self.emergency_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"❌ Emergency callback failed: {e}")
            
            logger.info("✅ Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Emergency cleanup failed: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("🔍 Starting system protection monitoring")
        
        while self.is_monitoring:
            try:
                health = self.get_system_health()
                
                # Check for emergency conditions
                if (health.cpu_percent > self.limits.emergency_threshold or 
                    health.memory_percent > self.limits.emergency_threshold):
                    
                    logger.critical(f"🚨 EMERGENCY: System overload detected!")
                    logger.critical(f"CPU: {health.cpu_percent:.1f}%, Memory: {health.memory_percent:.1f}%")
                    
                    self.emergency_cleanup()
                    
                    # If still overloaded, initiate shutdown
                    time.sleep(2)
                    health_after = self.get_system_health()
                    if (health_after.cpu_percent > self.limits.emergency_threshold or 
                        health_after.memory_percent > self.limits.emergency_threshold):
                        
                        logger.critical("🚨 SYSTEM SHUTDOWN INITIATED")
                        self._initiate_shutdown()
                        break
                
                # Check for warning conditions
                elif not health.is_healthy:
                    # Log warnings to file only, not to console to avoid interfering with chat
                    logger.info(f"⚠️ System health warning: {', '.join(health.warnings)}")
                    
                    # Call warning callbacks
                    for callback in self.warning_callbacks:
                        try:
                            callback(health)
                        except Exception as e:
                            logger.error(f"❌ Warning callback failed: {e}")
                
                # Periodic cleanup
                if datetime.now() - self.last_cleanup > self.cleanup_interval:
                    self._periodic_cleanup()
                    self.last_cleanup = datetime.now()
                
                time.sleep(self.limits.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                time.sleep(self.limits.check_interval)
    
    def _periodic_cleanup(self):
        """Perform periodic system cleanup"""
        try:
            # Garbage collection
            collected = gc.collect()
            if collected > 0:
                logger.info(f"🗑️ Periodic cleanup: {collected} objects collected")
            
            # Clear GPU cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
                
        except Exception as e:
            logger.error(f"❌ Periodic cleanup failed: {e}")
    
    def _initiate_shutdown(self):
        """Initiate graceful system shutdown"""
        # Demote to info to avoid console spam during interactive use
        logger.info("🛑 Initiating graceful shutdown...")
        
        try:
            # Stop monitoring
            self.stop_monitoring()
            
            # Final cleanup
            self.emergency_cleanup()
            
            # Exit gracefully
            logger.info("👋 System shutdown completed")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"❌ Shutdown failed: {e}")
            os._exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        try:
            logger.info(f"📡 Received signal {signum}, initiating shutdown...")
            self._initiate_shutdown()
        except Exception as e:
            logger.critical(f"❌ Signal handler failed: {e}")
            # Force exit if signal handling fails
            os._exit(1)


# Global system protection instance
_system_protection: Optional[SystemProtection] = None


def get_system_protection() -> SystemProtection:
    """Get global system protection instance"""
    global _system_protection
    if _system_protection is None:
        _system_protection = SystemProtection()
    return _system_protection


def start_system_protection():
    """Start global system protection"""
    protection = get_system_protection()
    protection.start_monitoring()
    return protection


def stop_system_protection():
    """Stop global system protection"""
    global _system_protection
    if _system_protection:
        _system_protection.stop_monitoring()
        _system_protection = None
