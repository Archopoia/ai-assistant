from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class HealthMetricsBase(BaseModel):
    weight_kg: Optional[float] = Field(default=None, gt=20, lt=500)
    weight_unit: Optional[str] = "kg"
    activity_frequency: Optional[int] = Field(default=None, ge=0, le=7)
    activity_duration: Optional[str] = None
    recorded_at: Optional[datetime] = None

    @field_validator("activity_duration")
    @classmethod
    def validate_duration(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        allowed = {"15-30min", "30-60min", "60+min"}
        if value not in allowed:
            raise ValueError("activity_duration must be one of: 15-30min, 30-60min, 60+min")
        return value

    @field_validator("weight_unit")
    @classmethod
    def validate_weight_unit(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.lower()
        if normalized not in {"kg", "lb", "lbs"}:
            raise ValueError("weight_unit must be one of: kg, lb, lbs")
        return normalized


class HealthMetricsCreate(HealthMetricsBase):
    pass


class HealthMetricsResponse(HealthMetricsBase):
    id: int
    user_id: int
    recorded_at: datetime
    bmi: Optional[float] = None
    wellness_score: Optional[float] = None
    goal_progress: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
