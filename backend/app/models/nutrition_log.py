from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=True, index=True)
    meal_label = Column(String, nullable=False, index=True)
    logged_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    calories_kcal = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, nullable=False, default=0.0)
    carbs_g = Column(Float, nullable=False, default=0.0)
    fats_g = Column(Float, nullable=False, default=0.0)
    micronutrients = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    user = relationship("User", back_populates="nutrition_logs")
