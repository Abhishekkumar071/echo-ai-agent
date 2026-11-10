"""Initial schema: users, sessions, conversations, messages, memories, search

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # ── sessions ──────────────────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_sessions_token", "sessions", ["token"])
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])

    # ── conversations ─────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False,
                  server_default="New Conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_conversations_user_id", "conversations", ["user_id"])
    op.create_index("idx_conversations_created_at", "conversations", ["created_at"],
                    postgresql_ops={"created_at": "DESC"})

    # ── messages ──────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("metadata", postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"],
                                ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_messages_role"),
    )
    op.create_index("idx_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("idx_messages_created_at", "messages", ["created_at"])

    # ── memories ──────────────────────────────────────────────────────────
    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("memory_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        # embedding nullable — ★ Change 2
        sa.Column("embedding", sa.Text, nullable=True),   # will be altered to vector(768) below
        sa.Column("embedding_failed", sa.Boolean, nullable=False,
                  server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("original_query", sa.Text, nullable=True),
        sa.Column("topic_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("related_conv_ids",
                  postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"],
                                ondelete="SET NULL"),
        sa.CheckConstraint(
            "memory_type IN ('short_term', 'long_term', 'temporal')",
            name="ck_memories_type",
        ),
    )
    # Convert embedding column to vector(768)
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector(768) USING NULL")
    # Partial IVFFlat index — only rows that have embeddings
    op.execute(
        "CREATE INDEX idx_memories_embedding ON memories "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100) "
        "WHERE embedding IS NOT NULL"
    )
    op.create_index("idx_memories_user_id", "memories", ["user_id"])
    op.create_index("idx_memories_type", "memories", ["memory_type"])
    op.create_index("idx_memories_created_at", "memories", ["created_at"])

    # ── search_queries ────────────────────────────────────────────────────
    op.create_table(
        "search_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"],
                                ondelete="SET NULL"),
    )
    op.create_index("idx_search_queries_conv", "search_queries", ["conversation_id"])

    # ── search_results ────────────────────────────────────────────────────
    op.create_table(
        "search_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("search_query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(1000), nullable=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("snippet", sa.Text, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("source_metadata", postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["search_query_id"], ["search_queries.id"],
                                ondelete="CASCADE"),
    )
    op.create_index("idx_search_results_query_id", "search_results", ["search_query_id"])
    op.create_unique_constraint(
        "uq_search_result_url_per_query",
        "search_results",
        ["search_query_id", "url"],
    )


def downgrade() -> None:
    op.drop_table("search_results")
    op.drop_table("search_queries")
    op.drop_table("memories")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("sessions")
    op.drop_table("users")
