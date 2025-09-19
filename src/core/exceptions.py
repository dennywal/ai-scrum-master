"""Custom exceptions for AI Scrum Master."""

from typing import Any


class AIScrumMasterError(Exception):
    """Base exception for AI Scrum Master."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


# Configuration Errors
class ConfigurationError(AIScrumMasterError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, config_item: str, reason: str):
        super().__init__(
            f"Configuration error for '{config_item}': {reason}",
            {"config_item": config_item, "reason": reason}
        )


# Validation Errors
class ValidationError(AIScrumMasterError):
    """Raised when input validation fails."""

    def __init__(self, field: str, reason: str, value: Any = None):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            {"field": field, "reason": reason, "value": value}
        )


# Document Processing Errors
class DocumentParsingError(AIScrumMasterError):
    """Raised when document parsing fails."""

    def __init__(self, document_type: str, reason: str):
        super().__init__(
            f"Failed to parse {document_type} document: {reason}",
            {"document_type": document_type, "reason": reason}
        )


class TaskExtractionError(AIScrumMasterError):
    """Raised when task extraction fails."""

    def __init__(self, source: str, reason: str):
        super().__init__(
            f"Failed to extract tasks from {source}: {reason}",
            {"source": source, "reason": reason}
        )


# LLM Errors
class LLMError(AIScrumMasterError):
    """Base class for LLM-related errors."""
    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM service fails."""

    def __init__(self, service: str, original_error: Exception):
        super().__init__(
            f"Failed to connect to {service}",
            {"service": service, "original_error": str(original_error)}
        )


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None):
        message = "LLM rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, {"retry_after": retry_after})


class LLMResponseError(LLMError):
    """Raised when LLM response is invalid."""

    def __init__(self, reason: str, response: Any = None):
        super().__init__(
            f"Invalid LLM response: {reason}",
            {"reason": reason, "response": response}
        )


# GitHub Errors
class GitHubError(AIScrumMasterError):
    """Base class for GitHub-related errors."""
    pass


class GitHubAuthenticationError(GitHubError):
    """Raised when GitHub authentication fails."""

    def __init__(self):
        super().__init__(
            "GitHub authentication failed. Please check your token.",
            {"required_scopes": ["repo", "write:issues"]}
        )


class GitHubRepositoryError(GitHubError):
    """Raised when repository operation fails."""

    def __init__(self, repo: str, reason: str):
        super().__init__(
            f"Repository operation failed for {repo}: {reason}",
            {"repository": repo, "reason": reason}
        )


class GitHubPermissionError(GitHubError):
    """Raised when lacking GitHub permissions."""

    def __init__(self, repo: str, operation: str):
        super().__init__(
            f"Insufficient permissions for {operation} on {repo}",
            {"repository": repo, "operation": operation}
        )


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(self, reset_time: int | None = None):
        message = "GitHub rate limit exceeded"
        if reset_time:
            from datetime import datetime
            reset_dt = datetime.fromtimestamp(reset_time)
            message += f". Resets at {reset_dt.isoformat()}"
        super().__init__(message, {"reset_time": reset_time})


class GitHubBatchCreationError(GitHubError):
    """Raised when batch issue creation partially fails."""

    def __init__(self, created: int, failed: int, errors: list):
        super().__init__(
            f"Batch creation partially failed: {created} created, {failed} failed",
            {"created": created, "failed": failed, "errors": errors}
        )


# Task Processing Errors
class DependencyError(AIScrumMasterError):
    """Raised when task dependency issues occur."""

    def __init__(self, reason: str, tasks: list | None = None):
        super().__init__(
            f"Dependency error: {reason}",
            {"reason": reason, "tasks": tasks}
        )


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected."""

    def __init__(self, cycle: list):
        super().__init__(
            "Circular dependency detected",
            cycle
        )


# Issue Generation Errors
class IssueGenerationError(AIScrumMasterError):
    """Raised when issue generation fails."""
    pass


# Retry Errors
class RetryExhaustedError(AIScrumMasterError):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, operation: str, attempts: int, last_error: Exception):
        super().__init__(
            f"All {attempts} retry attempts failed for {operation}",
            {
                "operation": operation,
                "attempts": attempts,
                "last_error": str(last_error)
            }
        )
