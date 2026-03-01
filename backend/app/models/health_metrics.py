from sqlalchemy import Column, Integer, Float, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class HealthMetrics(Base):
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Metrics
    weight_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    wellness_score = Column(Float, nullable=True)
    
    # Activity
    activity_frequency = Column(Integer, nullable=True)
    activity_duration = Column(String, nullable=True)
    
    # Goal progress
    goal_progress = Column(JSON, nullable=True)

    # Encrypted snapshot of metric payload (at-rest protection)
    encrypted_data = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="health_metrics")
