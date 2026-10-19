from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from src.database.db import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CapturedNote(Base):
    __tablename__ = "captured_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    source_type = Column(String(50), default="text") # text or voice
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TokenUsage(Base):
    """Registro mutable y auditable de consumo de tokens por modelo y función."""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    model_name = Column(String(100), nullable=False)
    feature = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    """Historial de mensajes para mantener memoria conversacional activa en multi-turn."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False) # 'user' o 'model'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
