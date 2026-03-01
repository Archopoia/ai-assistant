from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime
from zoneinfo import available_timezones
from .nutrition_constants import SUPPORTED_DIETARY_PREFERENCES, SUPPORTED_ALLERGIES_INTOLERANCES

ALLOWED_ACTIVITY_LEVELS = {"sedentary", "moderate", "active", "very_active"}
ALLOWED_GENDERS = {"male", "female", "other"}
ALLOWED_EXERCISE_TYPES = {"cardio", "strength", "flexibility", "sports"}
ALLOWED_SESSION_DURATIONS = {"15-30min", "30-60min", "60+min"}
ALLOWED_FITNESS_LEVELS = {"beginner", "intermediate", "advanced"}
ALLOWED_EXERCISE_ENVIRONMENTS = {"home", "gym", "outdoors"}
ALLOWED_TIME_PREFERENCES = {"morning", "afternoon", "evening"}


class HealthProfileBase(BaseModel):
    age: Optional[int] = Field(default=None, ge=13, le=120)
    gender: Optional[Literal["male", "female", "other"]] = None
    height_cm: Optional[float] = Field(default=None, gt=50, lt=300)
    weight_kg: Optional[float] = Field(default=None, gt=20, lt=500)
    occupation_type: Optional[str] = Field(default=None, min_length=2, max_length=80)
    activity_level: Optional[str] = None
    height_unit: Optional[Literal["cm", "in", "inches", "ft", "feet"]] = "cm"
    weight_unit: Optional[Literal["kg", "lb", "lbs"]] = "kg"
    dietary_preferences: Optional[Union[List[str], Dict[str, Any]]] = None
    dietary_restrictions: Optional[Union[List[str], Dict[str, Any]]] = None
    allergies_intolerances: Optional[List[str]] = None
    disliked_ingredients: Optional[List[str]] = None
    cuisine_preferences: Optional[List[str]] = None
    calorie_target_kcal: Optional[float] = Field(default=None, gt=800, lt=6000)
    macronutrient_targets: Optional[Dict[str, float]] = None
    meals_per_day: Optional[int] = Field(default=None, ge=1, le=10)
    meal_schedule: Optional[Dict[str, datetime]] = None
    timezone: Optional[str] = None
    fitness_goals: Optional[Dict[str, Any]] = None
    initial_assessment: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None

    @field_validator("activity_level")
    @classmethod
    def validate_activity_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().lower().replace(" ", "_")
        if normalized not in ALLOWED_ACTIVITY_LEVELS:
            raise ValueError(f"activity_level must be one of: {', '.join(sorted(ALLOWED_ACTIVITY_LEVELS))}")
        return normalized

    @field_validator("dietary_preferences", "dietary_restrictions")
    @classmethod
    def validate_dietary_data(cls, value: Optional[Union[List[str], Dict[str, Any]]]) -> Optional[Union[List[str], Dict[str, Any]]]:
        if value is None:
            return value
        if isinstance(value, list):
            return [str(v).strip().lower().replace(" ", "_") for v in value if str(v).strip()]
        if isinstance(value, dict):
            return value
        raise ValueError("Must be a list or object")

    @field_validator("allergies_intolerances")
    @classmethod
    def validate_allergies(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        normalized = [str(v).strip().lower().replace(" ", "_") for v in value if str(v).strip()]
        unknown = [item for item in normalized if item not in SUPPORTED_ALLERGIES_INTOLERANCES]
        if unknown:
            raise ValueError(f"Unsupported allergies/intolerances: {', '.join(unknown)}")
        return normalized

    @field_validator("disliked_ingredients", "cuisine_preferences")
    @classmethod
    def normalize_string_lists(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        return [str(v).strip().lower() for v in value if str(v).strip()]

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in available_timezones():
            raise ValueError("timezone must be a valid IANA timezone (e.g., Europe/Helsinki)")
        return value

    @model_validator(mode="after")
    def validate_nested_payloads(self):
        if isinstance(self.dietary_preferences, list):
            unknown = [item for item in self.dietary_preferences if item not in SUPPORTED_DIETARY_PREFERENCES]
            if unknown:
                raise ValueError(f"Unsupported dietary preferences: {', '.join(unknown)}")

        if self.macronutrient_targets:
            for macro in ("protein", "carbs", "fats"):
                if macro not in self.macronutrient_targets:
                    raise ValueError("macronutrient_targets must include protein, carbs, and fats")
                if float(self.macronutrient_targets[macro]) < 0:
                    raise ValueError(f"macronutrient_targets.{macro} must be non-negative")

        if self.fitness_goals:
            target_weight = self.fitness_goals.get("target_weight")
            if target_weight is not None and (target_weight <= 20 or target_weight >= 500):
                raise ValueError("fitness_goals.target_weight must be between 20 and 500 kg")

            target_activity = self.fitness_goals.get("target_activity_level")
            if target_activity is not None:
                target_activity_normalized = str(target_activity).strip().lower().replace(" ", "_")
                if target_activity_normalized not in ALLOWED_ACTIVITY_LEVELS:
                    raise ValueError("fitness_goals.target_activity_level is invalid")
                self.fitness_goals["target_activity_level"] = target_activity_normalized

        if self.initial_assessment:
            weekly_frequency = self.initial_assessment.get("weekly_activity_frequency")
            if weekly_frequency is not None and not (0 <= int(weekly_frequency) <= 7):
                raise ValueError("initial_assessment.weekly_activity_frequency must be between 0 and 7")

            exercise_types = self.initial_assessment.get("exercise_types")
            if exercise_types is not None:
                normalized_types = [str(t).strip().lower() for t in exercise_types]
                unknown = [t for t in normalized_types if t not in ALLOWED_EXERCISE_TYPES]
                if unknown:
                    raise ValueError(f"initial_assessment.exercise_types contains invalid values: {', '.join(unknown)}")
                self.initial_assessment["exercise_types"] = normalized_types

            session_duration = self.initial_assessment.get("session_duration")
            if session_duration is not None and session_duration not in ALLOWED_SESSION_DURATIONS:
                raise ValueError("initial_assessment.session_duration is invalid")

            fitness_level = self.initial_assessment.get("fitness_level")
            if fitness_level is not None and str(fitness_level).strip().lower() not in ALLOWED_FITNESS_LEVELS:
                raise ValueError("initial_assessment.fitness_level is invalid")

            exercise_environment = self.initial_assessment.get("exercise_environment")
            if exercise_environment is not None and str(exercise_environment).strip().lower() not in ALLOWED_EXERCISE_ENVIRONMENTS:
                raise ValueError("initial_assessment.exercise_environment is invalid")

            time_preference = self.initial_assessment.get("time_preference")
            if time_preference is not None and str(time_preference).strip().lower() not in ALLOWED_TIME_PREFERENCES:
                raise ValueError("initial_assessment.time_preference is invalid")

            endurance_minutes = self.initial_assessment.get("endurance_minutes")
            if endurance_minutes is not None and not (0 <= int(endurance_minutes) <= 600):
                raise ValueError("initial_assessment.endurance_minutes must be between 0 and 600")

            pushups_count = self.initial_assessment.get("pushups_count")
            if pushups_count is not None and not (0 <= int(pushups_count) <= 1000):
                raise ValueError("initial_assessment.pushups_count must be between 0 and 1000")

            squats_count = self.initial_assessment.get("squats_count")
            if squats_count is not None and not (0 <= int(squats_count) <= 1000):
                raise ValueError("initial_assessment.squats_count must be between 0 and 1000")

        if self.privacy_settings:
            for key in ("data_collection_consent", "data_sharing", "public_profile", "email_notifications"):
                if key in self.privacy_settings and not isinstance(self.privacy_settings[key], bool):
                    raise ValueError(f"privacy_settings.{key} must be boolean")

        return self


class HealthProfileCreate(HealthProfileBase):
    pass


class HealthProfileUpdate(HealthProfileBase):
    pass


class HealthProfileResponse(HealthProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
