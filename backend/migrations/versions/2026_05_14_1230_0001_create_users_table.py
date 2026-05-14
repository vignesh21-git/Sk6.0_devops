"""create users table

Revision ID: 0001
Revises:
Create Date: 2026-05-14 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgcrypto provides gen_random_uuid() used as the default for users.id.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
        sa.Column(
            "phone_verified",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "last_login_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'blocked', 'rejected')",
            name="ck_users_status",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'admin', 'superadmin')",
            name="ck_users_role",
        ),
    )
    op.create_index(
        "ix_users_phone", "users", ["phone"], unique=True
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index(
        "ix_users_last_login_at",
        "users",
        [sa.text("last_login_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_users_last_login_at", table_name="users")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")
