"""Domain errors raised by the business layer. The HTTP layer maps them to status codes."""


class DomainError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(DomainError):
    """The requested entity does not exist."""


class ConflictError(DomainError):
    """The request conflicts with the entity's current state."""


class RuleViolationError(DomainError):
    """The input is well-formed but breaks a business rule."""


class InvalidTransitionError(ConflictError):
    """A task status change that the state machine does not allow."""
