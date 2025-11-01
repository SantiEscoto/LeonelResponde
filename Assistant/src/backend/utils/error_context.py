#!/usr/bin/env python3
"""
Error Context Module
Contains ErrorContext class to avoid circular imports
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ErrorContext:
    """Context information for error handling"""

    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
