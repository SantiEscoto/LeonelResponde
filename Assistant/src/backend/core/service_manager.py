"""
Service Manager for coordinating component initialization and lifecycle management.
Provides centralized service management with dependency resolution and error handling.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass, field

from src.backend.utils.unified_logger import get_unified_logger
from src.backend.utils.error_handler import get_error_handler, ErrorCategory, ErrorSeverity


@dataclass
class ServiceConfig:
    """Configuration for a service component."""
    name: str
    init_function: Callable[[], Any]
    dependencies: List[str] = field(default_factory=list)
    required: bool = True
    retry_count: int = 3
    timeout: Optional[float] = None


class ServiceManager:
    """
    Manages initialization and lifecycle of application services.
    Handles dependency resolution, error recovery, and service status tracking.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the service manager."""
        self.logger = get_unified_logger("ServiceManager")
        self.error_handler = get_error_handler()
        self.services: Dict[str, Any] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.initialization_order: List[str] = []
        self.failed_services: Dict[str, Exception] = {}
        
    def register_service(self, config: ServiceConfig) -> None:
        """Register a service for initialization."""
        self.service_configs[config.name] = config
        self.logger.info(f"📝 Registered service: {config.name}")
        
    def initialize_all(self) -> Dict[str, Any]:
        """Initialize all registered services in dependency order."""
        self.logger.info("🚀 Starting service initialization...")
        
        # Resolve initialization order based on dependencies
        self._resolve_initialization_order()
        
        # Initialize services in order
        for service_name in self.initialization_order:
            self._initialize_service(service_name)
            
        # Report initialization results
        self._report_initialization_results()
        
        return self.services
        
    def get_service(self, name: str) -> Optional[Any]:
        """Get an initialized service by name."""
        return self.services.get(name)
        
    def is_service_available(self, name: str) -> bool:
        """Check if a service is available and initialized."""
        return name in self.services and self.services[name] is not None
        
    def shutdown_all(self) -> None:
        """Shutdown all services gracefully."""
        self.logger.info("🛑 Shutting down services...")
        
        # Shutdown in reverse order
        for service_name in reversed(self.initialization_order):
            service = self.services.get(service_name)
            if service and hasattr(service, 'shutdown'):
                try:
                    service.shutdown()
                    self.logger.info(f"✅ Shutdown {service_name}")
                except Exception as e:
                    self.logger.error(f"❌ Error shutting down {service_name}: {e}")
                    
    def _resolve_initialization_order(self) -> None:
        """Resolve service initialization order based on dependencies."""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(service_name: str):
            if service_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {service_name}")
            if service_name in visited:
                return
                
            temp_visited.add(service_name)
            
            config = self.service_configs.get(service_name)
            if config:
                for dependency in config.dependencies:
                    if dependency in self.service_configs:
                        visit(dependency)
                        
            temp_visited.remove(service_name)
            visited.add(service_name)
            order.append(service_name)
            
        for service_name in self.service_configs:
            if service_name not in visited:
                visit(service_name)
                
        self.initialization_order = order
        self.logger.info(f"📋 Initialization order: {' → '.join(order)}")
        
    def _initialize_service(self, service_name: str) -> None:
        """Initialize a single service with error handling and retries."""
        config = self.service_configs[service_name]
        
        # Check dependencies
        for dependency in config.dependencies:
            if not self.is_service_available(dependency):
                if config.required:
                    error_msg = f"Required dependency {dependency} not available for {service_name}"
                    self.logger.error(f"❌ {error_msg}")
                    self.failed_services[service_name] = RuntimeError(error_msg)
                    return
                else:
                    self.logger.warning(f"⚠️ Optional dependency {dependency} not available for {service_name}")
        
        # Initialize service with retries
        for attempt in range(config.retry_count):
            try:
                self.logger.info(f"🔧 Initializing {service_name} (attempt {attempt + 1}/{config.retry_count})")
                
                with self.error_handler.error_context(
                    service_name,
                    f"{service_name.lower()}_init"
                ):
                    service = config.init_function()
                    self.services[service_name] = service
                    self.logger.info(f"✅ {service_name} initialized successfully")
                    return
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize {service_name} (attempt {attempt + 1}): {e}")
                
                if attempt == config.retry_count - 1:
                    # Final attempt failed
                    self.failed_services[service_name] = e
                    if config.required:
                        self.logger.error(f"💥 Required service {service_name} failed to initialize")
                    else:
                        self.logger.warning(f"⚠️ Optional service {service_name} failed to initialize")
                        self.services[service_name] = None
                        
    def _report_initialization_results(self) -> None:
        """Report the results of service initialization."""
        successful = len([s for s in self.services.values() if s is not None])
        failed = len(self.failed_services)
        total = len(self.service_configs)
        
        self.logger.info(f"📊 Service initialization complete: {successful}/{total} successful")
        
        if failed > 0:
            self.logger.warning(f"⚠️ {failed} services failed to initialize:")
            for service_name, error in self.failed_services.items():
                config = self.service_configs[service_name]
                status = "CRITICAL" if config.required else "WARNING"
                self.logger.warning(f"  • {service_name}: {status} - {error}")