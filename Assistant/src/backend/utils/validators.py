#!/usr/bin/env python3
"""
Input Validation Module for LeonelResponde Assistant

This module provides comprehensive input validation and sanitization
for CLI commands, API requests, and knowledge base documents.

Author: LeonelResponde Team
Date: 2025-01-25
"""

import logging
import mimetypes
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""

    pass


class InputValidator:
    """Centralized input validation and sanitization"""

    # Security patterns
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript URLs
        r"on\w+\s*=",  # Event handlers
        r"\\x[0-9a-fA-F]{2}",  # Hex encoded chars
        r"\\u[0-9a-fA-F]{4}",  # Unicode encoded chars
        r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]",  # Control characters
    ]

    # File type restrictions
    ALLOWED_DOCUMENT_EXTENSIONS = {
        ".txt",
        ".md",
        ".pdf",
        ".doc",
        ".docx",
        ".json",
        ".csv",
        ".xml",
        ".html",
        ".htm",
    }

    ALLOWED_MIMETYPES = {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/json",
        "text/csv",
        "application/xml",
        "text/html",
    }

    # Size limits (in bytes)
    MAX_TEXT_LENGTH = 50000  # 50KB for text inputs
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB for documents
    MAX_QUERY_LENGTH = 2000  # 2KB for queries

    @classmethod
    def sanitize_text(cls, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input by removing dangerous patterns and limiting length

        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length (default: MAX_TEXT_LENGTH)

        Returns:
            Sanitized text

        Raises:
            ValidationError: If text contains dangerous patterns or exceeds limits
        """
        if not isinstance(text, str):
            raise ValidationError(f"Expected string, got {type(text).__name__}")

        # Check for empty or whitespace-only strings
        if not text.strip():
            raise ValidationError("Text cannot be empty or whitespace-only")

        # Apply length limit
        max_len = max_length or cls.MAX_TEXT_LENGTH
        if len(text) > max_len:
            raise ValidationError(f"Text exceeds maximum length of {max_len} characters")

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                raise ValidationError("Text contains potentially dangerous content")

        # Basic sanitization
        sanitized = text.strip()

        # Remove null bytes and other problematic characters
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        return sanitized

    @classmethod
    def validate_query(cls, query: str) -> str:
        """
        Validate and sanitize user queries

        Args:
            query: User query string

        Returns:
            Sanitized query

        Raises:
            ValidationError: If query is invalid
        """
        return cls.sanitize_text(query, cls.MAX_QUERY_LENGTH)

    @classmethod
    def validate_file_path(cls, file_path: Union[str, Path]) -> Path:
        """
        Validate file path for security and existence

        Args:
            file_path: Path to validate

        Returns:
            Validated Path object

        Raises:
            ValidationError: If path is invalid or unsafe
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Convert to absolute path and resolve
        try:
            file_path = file_path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValidationError(f"Invalid file path: {e}")

        # Check for path traversal attempts
        if ".." in str(file_path):
            raise ValidationError("Path traversal detected")

        # Ensure file exists
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")

        # Ensure it's a file, not a directory
        if not file_path.is_file():
            raise ValidationError("Path must be a file")

        # Check file size within limits
        file_size = file_path.stat().st_size
        if file_size > cls.MAX_DOCUMENT_SIZE:
            raise ValidationError(
                f"File size exceeds maximum allowed: {cls.MAX_DOCUMENT_SIZE} bytes"
            )

        # Validate file extension
        extension = file_path.suffix.lower()
        if extension not in cls.ALLOWED_DOCUMENT_EXTENSIONS:
            raise ValidationError(f"Unsupported file extension: {extension}")

        # Validate MIME type (warning only)
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type not in cls.ALLOWED_MIMETYPES:
            logger.warning(f"Potentially unsupported MIME type: {mime_type}")

        # Return the validated path
        return file_path

    @classmethod
    def validate_document(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate a document for knowledge base ingestion and return details.

        This runs the full path validation, enforces size and extension limits,
        and returns a structured dictionary with metadata.

        Args:
            file_path: Path to the document to validate.

        Returns:
            A dictionary with details about the validated document, including:
            - path: Path
            - size: int
            - extension: str
            - mime_type: Optional[str]
            - valid: bool

        Raises:
            ValidationError: If the document is invalid or unsafe.
        """
        path_obj = cls.validate_file_path(file_path)

        # Collect details after validation
        size = path_obj.stat().st_size
        extension = path_obj.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(path_obj))

        return {
            "path": path_obj,
            "size": size,
            "extension": extension,
            "mime_type": mime_type,
            "valid": True,
        }

    @classmethod
    def validate_api_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate API request parameters

        Args:
            params: Dictionary of parameters to validate

        Returns:
            Validated and sanitized parameters

        Raises:
            ValidationError: If parameters are invalid
        """
        validated: Dict[str, Any] = {}

        for key, value in params.items():
            # Sanitize key
            if not isinstance(key, str) or not key.strip():
                raise ValidationError(f"Invalid parameter key: {key}")

            clean_key = re.sub(r"[^a-zA-Z0-9_]", "", key.strip())
            if not clean_key:
                raise ValidationError(f"Invalid parameter key after sanitization: {key}")

            # Validate and sanitize value based on type
            if isinstance(value, str):
                validated[clean_key] = cls.sanitize_text(value)
            elif isinstance(value, (int, float, bool)):
                validated[clean_key] = value
            elif value is None:
                validated[clean_key] = None
            else:
                raise ValidationError(f"Unsupported parameter type for {key}: {type(value)}")

        return validated

    @classmethod
    def validate_cli_command(cls, command: str, args: List[str]) -> Dict[str, Any]:
        """
        Validate CLI command and arguments

        Args:
            command: Command name
            args: List of command arguments

        Returns:
            Validated command data

        Raises:
            ValidationError: If command or args are invalid
        """
        # Validate command name
        if not isinstance(command, str) or not command.strip():
            raise ValidationError("Command cannot be empty")

        clean_command = re.sub(r"[^a-zA-Z0-9_-]", "", command.strip())
        if not clean_command:
            raise ValidationError(f"Invalid command after sanitization: {command}")

        # Validate arguments
        clean_args: List[str] = []
        for arg in args:
            if isinstance(arg, str):
                # Allow more characters in args but still sanitize
                clean_arg = cls.sanitize_text(arg, max_length=1000)
                clean_args.append(clean_arg)
            else:
                raise ValidationError(f"Invalid argument type: {type(arg)}")

        return {"command": clean_command, "args": clean_args, "valid": True}


# Convenience functions for common validations


def validate_user_input(text: str) -> str:
    """Quick validation for general user input.

    Args:
        text: Raw user-provided text to sanitize.

    Returns:
        A sanitized version of the input text.

    Raises:
        ValidationError: If the input is empty, too long, or contains dangerous patterns.
    """
    return InputValidator.sanitize_text(text)


def validate_query_input(query: str) -> str:
    """Quick validation for user queries with query-specific limits.

    Args:
        query: The query string from the user.

    Returns:
        Sanitized query text not exceeding MAX_QUERY_LENGTH.

    Raises:
        ValidationError: If the query is invalid or unsafe.
    """
    return InputValidator.validate_query(query)


def validate_document_path(path: Union[str, Path]) -> Dict[str, Any]:
    """Quick validation for document paths intended for the knowledge base.

    Args:
        path: File path as a string or Path object.

    Returns:
        A dictionary containing details about the validated document (path, size,
        extension, mime_type, valid).

    Raises:
        ValidationError: If the path is invalid, the file is missing, too large,
        or of an unsupported type.
    """
    return InputValidator.validate_document(path)


def validate_api_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Quick validation for API request parameters.

    Args:
        params: Mapping of parameter names to values.

    Returns:
        A sanitized dictionary containing validated API parameters.

    Raises:
        ValidationError: If any parameter key or value is invalid or unsafe.
    """
    return InputValidator.validate_api_params(params)


def validate_cli_input(command: str, args: List[str]) -> Dict[str, Any]:
    """Quick validation for CLI command and arguments.

    Args:
        command: The CLI command name.
        args: A list of argument strings for the command.

    Returns:
        A dictionary with the sanitized command and arguments under keys:
        "command", "args", and a "valid" flag.

    Raises:
        ValidationError: If the command or any arguments are invalid.
    """
    return InputValidator.validate_cli_command(command, args)
