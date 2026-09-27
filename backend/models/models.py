from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Numeric, func, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# 1. Users Table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    connections = relationship("DatabaseConnection", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    dashboard_widgets = relationship("DashboardWidget", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    llm_usage_logs = relationship("LLMUsageLog", back_populates="user", cascade="all, delete-orphan")


# 2. Database Connections Table
class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    display_name = Column(String(100), nullable=False)
    db_type = Column(String(20), nullable=False, default="postgresql") # 'postgresql' | 'csv_import'
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    db_name = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True) # Must be a READ-ONLY role
    password_encrypted = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="connections")
    schema_cache = relationship("SchemaCache", back_populates="connection", cascade="all, delete-orphan")
    csv_uploads = relationship("CSVUpload", back_populates="connection", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="connection", cascade="all, delete-orphan")
    query_cache = relationship("QueryCache", back_populates="connection", cascade="all, delete-orphan")
    dashboard_widgets = relationship("DashboardWidget", back_populates="connection", cascade="all, delete-orphan")


# 3. Schema Cache Table (with embeddings for schema linking)
class SchemaCache(Base):
    __tablename__ = "schema_cache"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)
    is_primary_key = Column(Boolean, default=False)
    is_foreign_key = Column(Boolean, default=False)
    references_table = Column(String(100), nullable=True)
    ai_description = Column(Text, nullable=True)
    description_embedding = Column(Vector(768), nullable=True) # Gemini embedding dimension
    cached_at = Column(DateTime, default=func.now())

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="schema_cache")


# 4. CSV Uploads Table
class CSVUpload(Base):
    __tablename__ = "csv_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    table_name = Column(String(100), nullable=False)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=func.now())

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="csv_uploads")


# 5. Conversations Table
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), default="New Analysis")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="conversations")
    connection = relationship("DatabaseConnection", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


# 6. Messages Table
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(10), nullable=False) # 'user' | 'assistant'
    content = Column(Text, nullable=True)
    final_sql = Column(Text, nullable=True)
    query_result = Column(JSONB, nullable=True)
    analysis_result = Column(JSONB, nullable=True) # trend %, outliers, correlation notes
    chart_type = Column(String(20), nullable=True) # 'bar' | 'line' | 'pie' | 'stat_card'
    chart_config = Column(JSONB, nullable=True)
    was_successful = Column(Boolean, default=True)
    total_latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    agent_steps = relationship("AgentStep", back_populates="message", cascade="all, delete-orphan", order_by="AgentStep.step_number")
    bookmarks = relationship("Bookmark", back_populates="message", cascade="all, delete-orphan")
    llm_usage_logs = relationship("LLMUsageLog", back_populates="message", cascade="all, delete-orphan")


# 7. Agent Steps Table (Full Agentic Audit Trail)
class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(255), nullable=False) # 'intent_check','schema_linking','sql_generation','safety_validation','execution','self_correction','data_analysis','result_explanation'
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    reasoning = Column(Text, nullable=True)
    is_retry = Column(Boolean, default=False)
    retry_of = Column(Integer, ForeignKey("agent_steps.id", ondelete="SET NULL"), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    message = relationship("Message", back_populates="agent_steps")
    retried_step = relationship("AgentStep", remote_side=[id])


# 8. Query Cache Table (Semantic Caching)
class QueryCache(Base):
    __tablename__ = "query_cache"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_embedding = Column(Vector(768), nullable=False)
    generated_sql = Column(Text, nullable=False)
    hit_count = Column(Integer, default=1)
    last_used_at = Column(DateTime, default=func.now())

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="query_cache")


# 9. Dashboard Widgets Table
class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    sql_query = Column(Text, nullable=False)
    chart_type = Column(String(20), nullable=False)
    chart_config = Column(JSONB, nullable=True)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=1)
    height = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="dashboard_widgets")
    connection = relationship("DatabaseConnection", back_populates="dashboard_widgets")


# 10. Bookmarks Table
class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(200), nullable=False)
    folder = Column(String(100), default="General")
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="bookmarks")
    message = relationship("Message", back_populates="bookmarks")


# 11. LLM Usage Logs Table
class LLMUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String(20), nullable=False) # 'gemini' | 'groq'
    model_used = Column(String(50), nullable=False)
    step_type = Column(String(30), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="llm_usage_logs")
    message = relationship("Message", back_populates="llm_usage_logs")
