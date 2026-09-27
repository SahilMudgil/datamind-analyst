"""Widen step_type and chart_type columns to prevent truncation

Revision ID: 002_widen_step_type_columns
Revises: 001_initial_schema
Create Date: 2026-09-27 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_widen_step_type_columns'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        op.alter_column('agent_steps', 'step_type',
                        existing_type=sa.String(length=30),
                        type_=sa.String(length=255),
                        existing_nullable=False)
    except Exception:
        pass

    try:
        op.alter_column('llm_usage_logs', 'step_type',
                        existing_type=sa.String(length=30),
                        type_=sa.String(length=255),
                        existing_nullable=False)
    except Exception:
        pass

    try:
        op.alter_column('messages', 'chart_type',
                        existing_type=sa.String(length=20),
                        type_=sa.String(length=50),
                        existing_nullable=True)
    except Exception:
        pass

    try:
        op.alter_column('dashboard_widgets', 'chart_type',
                        existing_type=sa.String(length=20),
                        type_=sa.String(length=50),
                        existing_nullable=False)
    except Exception:
        pass


def downgrade() -> None:
    pass
