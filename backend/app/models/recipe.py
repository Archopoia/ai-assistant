from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    cuisine = Column(String, nullable=False, index=True)
    meal = Column(String, nullable=False, index=True)
    servings = Column(Integer, nullable=False, default=1)
    ingredients = Column(JSON, nullable=False, default=list)
    summary = Column(String, nullable=False)
    time = Column(Integer, nullable=False, default=30)
    difficulty_level = Column(String, nullable=False, default="easy")
    dietary_tags = Column(JSON, nullable=False, default=list)
    source = Column(String, nullable=False, default="rag-database")
    img = Column(String, nullable=True)
    preparation = Column(JSON, nullable=False, default=list)
    nutrition = Column(JSON, nullable=True)
    embedding = Column(JSON, nullable=True)
    rating_avg = Column(Float, nullable=True)
    rating_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
