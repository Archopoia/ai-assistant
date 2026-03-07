from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from .nutrition_constants import SUPPORTED_DIETARY_PREFERENCES, SUPPORTED_ALLERGIES_INTOLERANCES


class RecipeIngredient(BaseModel):
    id: str
    name: str
    quantity: float = Field(gt=0)
    unit: str = Field(default="gram")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"gram", "ml"}:
            raise ValueError("unit must be gram or ml")
        return normalized


class PreparationStep(BaseModel):
    step: str
    description: str
    ingredients: List[str]


class MicronutrientDetails(BaseModel):
    vitamin_d_mcg: float = Field(default=0, ge=0)
    vitamin_b12_mcg: float = Field(default=0, ge=0)
    iron_mg: float = Field(default=0, ge=0)


class CommunityFeedback(BaseModel):
    moderation_status: str = Field(default="approved")
    moderation_note: Optional[str] = None
    verified_recommendation: bool = False


class AntioxidantProfile(BaseModel):
    polyphenols: str = Field(default="medium")
    flavonoids: str = Field(default="medium")
    carotenoids: str = Field(default="medium")


class EnvironmentalImpact(BaseModel):
    carbon_footprint: str = Field(default="medium")
    water_usage: str = Field(default="medium")


class RecipeNutritionDetails(BaseModel):
    calories: float = Field(default=0, ge=0)
    protein: float = Field(default=0, ge=0)
    carbs: float = Field(default=0, ge=0)
    fats: float = Field(default=0, ge=0)
    fiber_g: float = Field(default=0, ge=0)
    sugar_g: float = Field(default=0, ge=0)
    sodium_mg: float = Field(default=0, ge=0)
    glycemic_index: int = Field(default=50, ge=0, le=100)
    antioxidant_profile: AntioxidantProfile = Field(default_factory=AntioxidantProfile)
    nutrient_density_score: float = Field(default=5.0, ge=0, le=10)
    processing_level: str = Field(default="minimally processed")
    environmental_impact: EnvironmentalImpact = Field(default_factory=EnvironmentalImpact)
    satiety_index: int = Field(default=50, ge=0, le=100)
    micronutrients: MicronutrientDetails = Field(default_factory=MicronutrientDetails)
    community_feedback: CommunityFeedback = Field(default_factory=CommunityFeedback)


class RecipeBase(BaseModel):
    id: str
    title: str
    cuisine: str
    meal: str
    servings: int = Field(ge=1, le=20)
    ingredients: List[RecipeIngredient]
    summary: str
    time: int = Field(ge=1, le=600)
    difficulty_level: str
    dietary_tags: List[str] = Field(default_factory=list)
    source: str
    img: Optional[str] = None
    preparation: List[PreparationStep]
    nutrition: Optional[RecipeNutritionDetails] = None

    @field_validator("dietary_tags")
    @classmethod
    def validate_tags(cls, value: List[str]) -> List[str]:
        normalized = [tag.strip().lower().replace(" ", "_") for tag in value]
        unknown = [tag for tag in normalized if tag not in SUPPORTED_DIETARY_PREFERENCES]
        if unknown:
            raise ValueError(f"Unsupported dietary tags: {', '.join(unknown)}")
        return normalized


class RecipeSearchFilters(BaseModel):
    q: Optional[str] = None
    cuisine: Optional[str] = None
    ingredients: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    max_calories: Optional[float] = Field(default=None, gt=0)
    min_protein: Optional[float] = Field(default=None, ge=0)
    max_protein: Optional[float] = Field(default=None, ge=0)
    min_carbs: Optional[float] = Field(default=None, ge=0)
    max_carbs: Optional[float] = Field(default=None, ge=0)
    min_fats: Optional[float] = Field(default=None, ge=0)
    max_fats: Optional[float] = Field(default=None, ge=0)
    max_prep_time: Optional[int] = Field(default=None, ge=1)

    @field_validator("allergies")
    @classmethod
    def validate_allergies(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        normalized = [item.strip().lower().replace(" ", "_") for item in value]
        unknown = [item for item in normalized if item not in SUPPORTED_ALLERGIES_INTOLERANCES]
        if unknown:
            raise ValueError(f"Unsupported allergies: {', '.join(unknown)}")
        return normalized


class RecipeGenerateRequest(BaseModel):
    prompt: str
    meal: Optional[str] = None
    cuisine: Optional[str] = None
    servings: int = Field(default=2, ge=1, le=20)


class RecipeSubstitutionRequest(BaseModel):
    recipe_id: str
    ingredient_name: str
    available_ingredients: Optional[List[str]] = None


class RecipePortionRequest(BaseModel):
    recipe_id: str
    servings: int = Field(ge=1, le=50)


class RecipeResponse(RecipeBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rating_avg: Optional[float] = None
    rating_count: int = 0
    moderation_status: str = "approved"
    is_verified: bool = False

    class Config:
        from_attributes = True
