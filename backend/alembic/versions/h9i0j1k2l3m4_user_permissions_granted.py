"""Add granted column to user_permissions for deny-override support.

Until now user_permissions stored only ADDITIVE overrides on top of the
role template. Admins could grant extra permissions to a user but could
never revoke a role-granted one. This migration introduces a `granted`
flag so a row can also encode a DENY: the user has that role permission
taken away.

Effective permissions become: (role_template union grants) minus denies.

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l4
Create Date: 2026-04-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "h9i0j1k2l3m4"
down_revision: Union[str, Sequence[str], None] = "g8h9i0j1k2l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_permissions",
        sa.Column(
            "granted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_permissions", "granted")
