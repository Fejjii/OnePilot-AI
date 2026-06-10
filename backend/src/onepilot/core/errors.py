class OnePilotError(Exception):
    """Base for all app errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(OnePilotError):
    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
        status_code: int = 404,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class PermissionDeniedError(OnePilotError):
    def __init__(
        self,
        message: str = "Permission denied",
        code: str = "PERMISSION_DENIED",
        status_code: int = 403,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class AuthenticationError(OnePilotError):
    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "AUTHENTICATION_ERROR",
        status_code: int = 401,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class QuotaExceededError(OnePilotError):
    def __init__(
        self,
        message: str = "Quota exceeded",
        code: str = "QUOTA_EXCEEDED",
        status_code: int = 429,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class RateLimitExceededError(OnePilotError):
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        status_code: int = 429,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class ValidationError(OnePilotError):
    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
        status_code: int = 422,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class ProviderUnavailableError(OnePilotError):
    def __init__(
        self,
        message: str = "External provider is unavailable",
        code: str = "PROVIDER_UNAVAILABLE",
        status_code: int = 503,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class GuardrailBlockedError(OnePilotError):
    def __init__(
        self,
        message: str = "Request blocked by guardrail",
        code: str = "GUARDRAIL_BLOCKED",
        status_code: int = 400,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class ConflictError(OnePilotError):
    def __init__(
        self,
        message: str = "Resource conflict",
        code: str = "CONFLICT",
        status_code: int = 409,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)
