from datetime import datetime, date
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from .nutrition_constants import SUPPORTED_DIETARY_PREFERENCES, SUPPORTED_ALLERGIES_INTOLERANCES


class MealPlanPreferences(BaseModel):
    dietary_restrictions: List[str] = Field(default_factory=list)
    allergies_intolerances: List[str] = Field(default_factory=list)
    cuisine_preferences: List[str] = Field(default_factory=list)
    disliked_ingredients: List[str] = Field(default_factory=list)
    calorie_target: float = Field(gt=800, lt=6000)
    macronutrient_targets: Dict[str, float]
    meals_per_day: int = Field(ge=1, le=10)
    preferred_meal_times: Dict[str, datetime]
    timezone: str

    @field_validator("dietary_restrictions")
    @classmethod
    def validate_restrictions(cls, value: List[str]) -> List[str]:
        normalized = [item.strip().lower().replace(" ", "_") for item in value]
        unknown = [item for item in normalized if item not in SUPPORTED_DIETARY_PREFERENCES]
        if unknown:
            raise ValueError(f"Unsupported dietary restrictions: {', '.join(unknown)}")
        return normalized

    @field_validator("allergies_intolerances")
    @classmethod
    def validate_allergies(cls, value: List[str]) -> List[str]:
        normalized = [item.strip().lower().replace(" ", "_") for item in value]
        unknown = [item for item in normalized if item not in SUPPORTED_ALLERGIES_INTOLERANCES]
        if unknown:
            raise ValueError(f"Unsupported allergies/intolerances: {', '.join(unknown)}")
        return normalized


class MealPlanRequest(BaseModel):
    duration: Literal["daily", "weekly"]
    date: date
    version: str = "1.0"
    created_at: datetime


class MealPlanGenerateRequest(BaseModel):
    user_preferences: MealPlanPreferences
    meal_plan_request: MealPlanRequest


class MealEntry(BaseModel):
    id: str
    name: str
    meal_type: str
    scheduled_at: datetime
    nutrition: Dict[str, Any]
    recipe_id: Optional[str] = None
    ingredients: Optional[List[Dict[str, Any]]] = None


class MealPlanResponse(BaseModel):
    id: int
    user_id: int
    duration: str
    target_date: str
    timezone: str
    version: str
    meals: List[MealEntry]
    alternatives: Optional[Dict[str, List[MealEntry]]] = None
    strategy: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MealSwapRequest(BaseModel):
    source_meal_id: str
    target_meal_id: str


class MealRegenerateRequest(BaseModel):
    meal_id: Optional[str] = None
    regenerate_all: bool = False


class MealManualAddRequest(BaseModel):
    day_iso: str
    meal: MealEntry


class MealPlanVersionResponse(BaseModel):
    id: int
    meal_plan_id: int
    user_id: int
    version: str
    snapshot: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
