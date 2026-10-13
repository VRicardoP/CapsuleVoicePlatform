"""initial schema baseline

Revision ID: 8e4c17fbcac1
Revises:
Create Date: 2026-02-25 10:02:23.925057

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e4c17fbcac1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline stamp — schema created by sferaai.sql + Base.metadata.create_all.

    This migration is intentionally empty. It serves as the Alembic baseline
    for databases that predate the migration system. Run `alembic stamp head`
    on existing databases to mark them as current without executing DDL.

    Tables NOT managed by ORM (created via raw SQL post-deploy):
    - user_preferences, secure_keys, encryption_keys, client_error_logs
    - decrypt_pii_with_metadata() function
    See docs/CHANGELOG_ORM_SQL_ALIGNMENT.md for details.
    """
    pass


def downgrade() -> None:
    """No downgrade — baseline cannot be reverted."""
    pass
