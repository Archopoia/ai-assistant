from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    duration = Column(String, nullable=False, index=True)  # daily|weekly
    target_date = Column(String, nullable=False, index=True)  # ISO date
    timezone = Column(String, nullable=False, default="UTC")
    version = Column(String, nullable=False, default="1.0")
    meals = Column(JSON, nullable=False, default=list)
    alternatives = Column(JSON, nullable=True)
    strategy = Column(JSON, nullable=True)
    nutritional_balance_score = Column(Float, nullable=True)
    diversity_index = Column(Float, nullable=True)
    micronutrient_coverage = Column(JSON, nullable=True)
    weekly_trends = Column(JSON, nullable=True)
    sustainability_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="meal_plans")


class MealPlanVersion(Base):
    __tablename__ = "meal_plan_versions"

    id = Column(Integer, primary_key=True, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    version = Column(String, nullable=False, index=True)
    snapshot = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
