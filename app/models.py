from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id = Column(String, primary_key=True)
    prompt = Column(Text, nullable=False)
    status = Column(String, default="pending")
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())