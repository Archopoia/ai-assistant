from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Demographics
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    
    # Physical metrics
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    
    # Lifestyle
    occupation_type = Column(String, nullable=True)
    activity_level = Column(String, nullable=True)
    
    # Dietary
    dietary_preferences = Column(JSON, nullable=True)
    dietary_restrictions = Column(JSON, nullable=True)
    allergies_intolerances = Column(JSON, nullable=True)
    disliked_ingredients = Column(JSON, nullable=True)
    cuisine_preferences = Column(JSON, nullable=True)
    calorie_target_kcal = Column(Float, nullable=True)
    macronutrient_targets = Column(JSON, nullable=True)
    meals_per_day = Column(Integer, nullable=True)
    meal_schedule = Column(JSON, nullable=True)
    timezone = Column(String, nullable=True)
    
    # Fitness goals
    fitness_goals = Column(JSON, nullable=True)
    
    # Initial assessment
    initial_assessment = Column(JSON, nullable=True)
    
    # Privacy settings
    privacy_settings = Column(JSON, nullable=True)

    # Encrypted snapshot of full profile payload (at-rest protection)
    encrypted_data = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="health_profile")
