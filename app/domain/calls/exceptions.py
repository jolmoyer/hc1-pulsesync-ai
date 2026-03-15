class CallNotFoundError(Exception):
    """Raised when a call record cannot be located by ID or external ID."""


class InvalidCallStateError(Exception):
    """Raised when an operation is attempted on a call in an incompatible state."""
