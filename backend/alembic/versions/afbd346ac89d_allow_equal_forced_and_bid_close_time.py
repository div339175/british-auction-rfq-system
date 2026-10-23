"""allow_equal_forced_and_bid_close_time

Revision ID: afbd346ac89d
Revises: 6309a2e136ac
Create Date: 2026-10-23 13:22:09.272374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afbd346ac89d'
down_revision: Union[str, Sequence[str], None] = '6309a2e136ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update chk_forced_after_close to allow bid_close_time == forced_bid_close_time."""
    op.drop_constraint('chk_forced_after_close', 'rfqs', type_='check')
    op.create_check_constraint(
        'chk_forced_after_close',
        'rfqs',
        'forced_bid_close_time >= bid_close_time'
    )


def downgrade() -> None:
    """Revert chk_forced_after_close to strict inequality."""
    op.drop_constraint('chk_forced_after_close', 'rfqs', type_='check')
    op.create_check_constraint(
        'chk_forced_after_close',
        'rfqs',
        'forced_bid_close_time > bid_close_time'
    )
