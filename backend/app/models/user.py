from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # OAuth
    oauth_google_id = Column(String, unique=True, nullable=True, index=True)
    oauth_github_id = Column(String, unique=True, nullable=True, index=True)
    
    # 2FA
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String, nullable=True)

    # Email verification / password reset token metadata
    email_verification_token_hash = Column(String, nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token_hash = Column(String, nullable=True, index=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False)
    health_metrics = relationship("HealthMetrics", back_populates="user")
    ai_insights = relationship("AIInsights", back_populates="user")
    meal_plans = relationship("MealPlan", back_populates="user")
    nutrition_logs = relationship("NutritionLog", back_populates="user")
    assistant_conversations = relationship("AssistantConversation", back_populates="user")
