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
