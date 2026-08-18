from mobility_guard.application.ports import TransactionRepository
from mobility_guard.config import Settings
from mobility_guard.infrastructure.sqlalchemy_repository import (
    SQLAlchemyTransactionRepository,
)
from mobility_guard.infrastructure.sqlite_repository import SQLiteTransactionRepository


def build_repository(settings: Settings) -> TransactionRepository:
    if settings.database_url:
        return SQLAlchemyTransactionRepository(
            settings.database_url,
            create_schema=settings.app_env != "production",
        )
    return SQLiteTransactionRepository(settings.database_path)
