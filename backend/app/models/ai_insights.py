from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class AIInsights(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    insight_type = Column(String, nullable=False)  # health_status, progress_evaluation, recommendations, weekly_summary
    content = Column(JSON, nullable=False)
    version = Column(String, nullable=True)
    context_snapshot = Column(JSON, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ai_insights")
