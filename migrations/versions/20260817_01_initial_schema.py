"""Create transactions table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("customer_id", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("merchant", sa.String(length=120), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("anomaly_threshold", sa.Float(), nullable=False),
        sa.Column("anomaly_reasons", sa.JSON(), nullable=False),
        sa.Column("anomaly_explanation", sa.Text(), nullable=False),
        sa.Column(
            "enrichment_status",
            sa.String(length=20),
            server_default="skipped",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(
        "idx_transactions_customer_occurred",
        "transactions",
        ["customer_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_transactions_customer_occurred", table_name="transactions")
    op.drop_table("transactions")
