class DomainException(Exception):
    """Base exception for all domain-related errors in ai-reasoning-service."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AlignmentException(DomainException):
    """Raised when an error occurs during the biological alignment evaluation."""
    pass


class EntityValidationException(DomainException):
    """Raised when biological entity data is malformed or invalid."""
    pass
