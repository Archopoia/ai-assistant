from datetime import datetime, date
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class NutritionLogCreate(BaseModel):
    meal_plan_id: Optional[int] = None
    meal_label: str
    logged_at: datetime
    calories_kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fats_g: float = Field(ge=0)
    micronutrients: Optional[Dict[str, float]] = None


class NutritionLogResponse(NutritionLogCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class NutritionDailySummary(BaseModel):
    date: date
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fats_g: float
    calorie_target_kcal: float
    deficit_surplus_kcal: float
    protein_target_pct: float
    carbs_target_pct: float
    fats_target_pct: float
    micronutrients: Dict[str, float]
    micronutrient_recommended: Dict[str, float]
    micronutrient_target_pct: Dict[str, float]


class NutritionTrendPoint(BaseModel):
    date: date
    deficit_surplus_kcal: float


class NutritionTrendResponse(BaseModel):
    points: List[NutritionTrendPoint]
