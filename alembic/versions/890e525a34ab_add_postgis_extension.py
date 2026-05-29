"""Add postgis extension.

Revision ID: 890e525a34ab
Revises: 358384b5ab77
Create Date: 2026-05-27 14:47:13.277828
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "890e525a34ab"
down_revision: Union[str, Sequence[str], None] = "358384b5ab77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
