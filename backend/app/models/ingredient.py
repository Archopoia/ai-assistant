from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, nullable=False, index=True)
    unit = Column(String, nullable=False, default="gram")
    quantity = Column(Float, nullable=False, default=100.0)
    nutrition = Column(JSON, nullable=False, default=dict)
    category = Column(String, nullable=True, index=True)
    aliases = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
