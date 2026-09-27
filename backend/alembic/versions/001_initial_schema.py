"""Initial schema creation with 11 tables and vector extension

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-21 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 0. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(length=100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # 2. Database Connections
    op.create_table(
        'database_connections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('db_type', sa.String(length=20), nullable=False, server_default='postgresql'),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('db_name', sa.String(length=100), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('password_encrypted', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 3. Schema Cache
    op.create_table(
        'schema_cache',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('connection_id', sa.Integer(), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('column_name', sa.String(length=100), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('is_primary_key', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('is_foreign_key', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('references_table', sa.String(length=100), nullable=True),
        sa.Column('ai_description', sa.Text(), nullable=True),
        sa.Column('description_embedding', Vector(768), nullable=True),
        sa.Column('cached_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 4. CSV Uploads
    op.create_table(
        'csv_uploads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_id', sa.Integer(), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('row_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('column_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 5. Conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_id', sa.Integer(), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=200), server_default='New Analysis', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )

    # 6. Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('final_sql', sa.Text(), nullable=True),
        sa.Column('query_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('chart_type', sa.String(length=20), nullable=True),
        sa.Column('chart_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('was_successful', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('total_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 7. Agent Steps
    op.create_table(
        'agent_steps',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(length=30), nullable=False),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('is_retry', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('retry_of', sa.Integer(), sa.ForeignKey('agent_steps.id', ondelete='SET NULL'), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 8. Query Cache
    op.create_table(
        'query_cache',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('connection_id', sa.Integer(), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_embedding', Vector(768), nullable=False),
        sa.Column('generated_sql', sa.Text(), nullable=False),
        sa.Column('hit_count', sa.Integer(), server_default='1', nullable=True),
        sa.Column('last_used_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 9. Dashboard Widgets
    op.create_table(
        'dashboard_widgets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_id', sa.Integer(), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('sql_query', sa.Text(), nullable=False),
        sa.Column('chart_type', sa.String(length=20), nullable=False),
        sa.Column('chart_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('position_x', sa.Integer(), server_default='0', nullable=True),
        sa.Column('position_y', sa.Integer(), server_default='0', nullable=True),
        sa.Column('width', sa.Integer(), server_default='1', nullable=True),
        sa.Column('height', sa.Integer(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 10. Bookmarks
    op.create_table(
        'bookmarks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=False),
        sa.Column('folder', sa.String(length=100), server_default='General', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # 11. LLM Usage Logs
    op.create_table(
        'llm_usage_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('model_used', sa.String(length=50), nullable=False),
        sa.Column('step_type', sa.String(length=30), nullable=False),
        sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=True),
        sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=True),
        sa.Column('estimated_cost_usd', sa.Numeric(precision=10, scale=6), server_default='0', nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    # Vector Indexes (ivfflat)
    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_schema_cache_embedding ON schema_cache USING ivfflat (description_embedding vector_cosine_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS idx_query_cache_embedding ON query_cache USING ivfflat (question_embedding vector_cosine_ops);")
    except Exception:
        pass


def downgrade() -> None:
    op.drop_table('llm_usage_logs')
    op.drop_table('bookmarks')
    op.drop_table('dashboard_widgets')
    op.drop_table('query_cache')
    op.drop_table('agent_steps')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('csv_uploads')
    op.drop_table('schema_cache')
    op.drop_table('database_connections')
    op.drop_table('users')
