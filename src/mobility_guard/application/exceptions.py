class ApplicationError(Exception):
    """Base exception for expected application errors."""


class DuplicateTransactionError(ApplicationError):
    pass


class TransactionNotFoundError(ApplicationError):
    pass

