"""Application-level error classes."""


class AppError(Exception):
    """Raised for expected, user-facing errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
