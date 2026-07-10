"""add payment_intent_id -> PaymentModel

Revision ID: a1f3e9b7c2d4
Revises: c3dd44bbd6cd
Create Date: 2026-07-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f3e9b7c2d4'
down_revision: Union[str, None] = 'c3dd44bbd6cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'payments',
        sa.Column('payment_intent_id', sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f('ix_payments_payment_intent_id'),
        'payments',
        ['payment_intent_id'],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_payments_payment_intent_id'), table_name='payments')
    op.drop_column('payments', 'payment_intent_id')
