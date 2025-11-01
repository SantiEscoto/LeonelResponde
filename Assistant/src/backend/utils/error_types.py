#!/usr/bin/env python3
"""
Error Types and Enums for LeonelResponde Assistant

This module contains the core error type definitions to avoid circular imports.
"""

from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification"""
    SYSTEM = "system"
    NETWORK = "network"
    MODEL = "model"
    MEMORY = "memory"
    VALIDATION = "validation"
    BUSINESS = "business"
    CONFIG = "config"
    IO = "io"
