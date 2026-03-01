from typing import Dict, Any, Optional
from ..models.health_profile import HealthProfile
from ..models.health_metrics import HealthMetrics


def normalize_weight_to_kg(weight: float, unit: str = "kg") -> float:
    """Convert weight to kilograms."""
    if unit.lower() == "lb" or unit.lower() == "lbs":
        return weight * 0.453592
    return weight


def normalize_height_to_cm(height: float, unit: str = "cm") -> float:
    """Convert height to centimeters."""
    if unit.lower() == "in" or unit.lower() == "inches":
        return height * 2.54
    elif unit.lower() == "ft" or unit.lower() == "feet":
        return height * 30.48
    return height


def standardize_activity_level(activity_level: str) -> str:
    """Standardize activity level values."""
    level_lower = activity_level.lower()
    if level_lower in ["sedentary", "low", "inactive"]:
        return "sedentary"
    elif level_lower in ["light", "lightly active", "moderate"]:
        return "moderate"
    elif level_lower in ["very active", "very_active", "extremely active"]:
        return "very_active"
    elif level_lower in ["active", "high"]:
        return "active"
    return "moderate"


def normalize_dietary_data(preferences: Optional[Dict[str, Any]], restrictions: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize dietary preferences and restrictions."""
    normalized = {
        "preferences": [],
        "restrictions": []
    }
    
    if preferences:
        if isinstance(preferences, list):
            normalized["preferences"] = [str(p).lower().replace(" ", "_") for p in preferences]
        elif isinstance(preferences, dict):
            normalized["preferences"] = [str(k).lower().replace(" ", "_") for k, v in preferences.items() if v]
    
    if restrictions:
        if isinstance(restrictions, list):
            normalized["restrictions"] = [str(r).lower().replace(" ", "_") for r in restrictions]
        elif isinstance(restrictions, dict):
            normalized["restrictions"] = [str(k).lower().replace(" ", "_") for k, v in restrictions.items() if v]
    
    return normalized


def prepare_ai_data(health_profile: HealthProfile, recent_metrics: list[HealthMetrics], goals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Prepare normalized data for AI processing, removing PII."""
    
    # Normalize current state
    current_state = {}
    if health_profile.weight_kg:
        current_state["weight"] = health_profile.weight_kg
    if health_profile.activity_level:
        current_state["activity_level"] = standardize_activity_level(health_profile.activity_level)
    if health_profile.height_cm:
        current_state["height_cm"] = health_profile.height_cm
    
    # Normalize target state from goals
    target_state = {}
    if goals:
        if "target_weight" in goals:
            target_state["weight"] = goals["target_weight"]
        if "target_activity_level" in goals:
            target_state["activity_level"] = standardize_activity_level(str(goals["target_activity_level"]))
    
    # Get preferences and restrictions
    dietary_data = normalize_dietary_data(
        health_profile.dietary_preferences,
        health_profile.dietary_restrictions
    )
    
    # Build progress history (without PII)
    progress_history = []
    for metric in recent_metrics[-10:]:  # Last 10 entries
        entry = {}
        if metric.weight_kg:
            entry["weight"] = metric.weight_kg
        if metric.bmi:
            entry["bmi"] = metric.bmi
        if metric.wellness_score:
            entry["wellness_score"] = metric.wellness_score
        if metric.activity_frequency:
            entry["activity_frequency"] = metric.activity_frequency
        if metric.recorded_at:
            entry["date"] = metric.recorded_at.isoformat()
        progress_history.append(entry)
    
    # Structure for AI consumption
    ai_data = {
        "user_metrics": {
            "current_state": current_state,
            "target_state": target_state,
            "preferences": dietary_data["preferences"],
            "restrictions": dietary_data["restrictions"],
            "meal_preferences": {
                "allergies_intolerances": health_profile.allergies_intolerances or [],
                "disliked_ingredients": health_profile.disliked_ingredients or [],
                "cuisine_preferences": health_profile.cuisine_preferences or [],
                "calorie_target_kcal": health_profile.calorie_target_kcal,
                "macronutrient_targets": health_profile.macronutrient_targets or {},
                "meals_per_day": health_profile.meals_per_day,
                "meal_schedule": health_profile.meal_schedule or {},
                "timezone": health_profile.timezone,
            },
            "progress_history": progress_history,
            "goals": goals or {},
            "privacy": {
                "data_sharing": bool((health_profile.privacy_settings or {}).get("data_sharing", True)),
                "public_profile": bool((health_profile.privacy_settings or {}).get("public_profile", False))
            }
        }
    }
    
    return ai_data
