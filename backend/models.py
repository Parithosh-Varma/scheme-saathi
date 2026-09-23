import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from .database import Base


def _uuid():
    return str(uuid.uuid4())


class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(String, primary_key=True, default=_uuid)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    language_preference = Column(String, default="hi")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    query_count = Column(Integer, default=0)


class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("user_sessions.id"), nullable=True)
    phone_number = Column(String, default="demo")
    input_type = Column(String, default="text")
    input_language = Column(String, default="hi")
    query_text = Column(Text, default="")
    schemes_matched = Column(Integer, default=0)
    scheme_ids = Column(JSON, default=list)
    response_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
