from typing import Any, Optional
from fastapi import HTTPException, status


class PortalException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        data: Optional[Any] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or "PORTAL_ERROR"
        self.data = data


class AuthenticationError(PortalException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_FAILED",
        )


class PermissionDeniedError(PortalException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="PERMISSION_DENIED",
        )


class CSRFValidationError(PortalException):
    def __init__(self, detail: str = "Invalid or missing CSRF token"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="CSRF_VALIDATION_FAILED",
        )


class NotFoundError(PortalException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
        )


class SupersetIntegrationError(PortalException):
    def __init__(self, detail: str = "Superset service communication error"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code="SUPERSET_ERROR",
        )
