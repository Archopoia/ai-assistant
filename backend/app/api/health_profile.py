from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..api import get_current_user
from ..models.user import User
from ..models.health_profile import HealthProfile
from ..schemas.health_profile import HealthProfileCreate, HealthProfileUpdate, HealthProfileResponse
from ..services.data_normalizer import standardize_activity_level, normalize_height_to_cm, normalize_weight_to_kg
from ..services.data_protection import encrypt_json_payload

router = APIRouter(prefix="/health-profile", tags=["health-profile"])


@router.get("", response_model=HealthProfileResponse)
async def get_health_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's health profile."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    return profile


@router.post("", response_model=HealthProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_health_profile(
    profile_data: HealthProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update health profile."""
    existing_profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    payload = profile_data.model_dump()
    payload.pop("height_unit", None)
    payload.pop("weight_unit", None)
    if profile_data.height_cm:
        payload["height_cm"] = normalize_height_to_cm(profile_data.height_cm, profile_data.height_unit or "cm")
    if profile_data.weight_kg:
        payload["weight_kg"] = normalize_weight_to_kg(profile_data.weight_kg, profile_data.weight_unit or "kg")
    if payload.get("activity_level"):
        payload["activity_level"] = standardize_activity_level(payload["activity_level"])
    if payload.get("fitness_goals") and payload["fitness_goals"].get("target_activity_level"):
        payload["fitness_goals"]["target_activity_level"] = standardize_activity_level(
            str(payload["fitness_goals"]["target_activity_level"])
        )
    
    privacy_settings = payload.get("privacy_settings") or {}
    if not existing_profile and privacy_settings.get("data_collection_consent") is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit data collection consent is required before creating a health profile"
        )

    if existing_profile:
        # Update existing profile
        update_payload = profile_data.model_dump(exclude_unset=True)
        update_payload.pop("height_unit", None)
        update_payload.pop("weight_unit", None)
        if "height_cm" in update_payload and update_payload["height_cm"] is not None:
            update_payload["height_cm"] = normalize_height_to_cm(
                update_payload["height_cm"], profile_data.height_unit or "cm"
            )
        if "weight_kg" in update_payload and update_payload["weight_kg"] is not None:
            update_payload["weight_kg"] = normalize_weight_to_kg(
                update_payload["weight_kg"], profile_data.weight_unit or "kg"
            )
        for key, value in update_payload.items():
            setattr(existing_profile, key, value)
        if existing_profile.activity_level:
            existing_profile.activity_level = standardize_activity_level(existing_profile.activity_level)
        if existing_profile.fitness_goals and existing_profile.fitness_goals.get("target_activity_level"):
            existing_profile.fitness_goals["target_activity_level"] = standardize_activity_level(
                str(existing_profile.fitness_goals["target_activity_level"])
            )
        existing_profile.encrypted_data = encrypt_json_payload({
            "age": existing_profile.age,
            "gender": existing_profile.gender,
            "height_cm": existing_profile.height_cm,
            "weight_kg": existing_profile.weight_kg,
            "occupation_type": existing_profile.occupation_type,
            "activity_level": existing_profile.activity_level,
            "dietary_preferences": existing_profile.dietary_preferences,
            "dietary_restrictions": existing_profile.dietary_restrictions,
            "allergies_intolerances": existing_profile.allergies_intolerances,
            "disliked_ingredients": existing_profile.disliked_ingredients,
            "cuisine_preferences": existing_profile.cuisine_preferences,
            "calorie_target_kcal": existing_profile.calorie_target_kcal,
            "macronutrient_targets": existing_profile.macronutrient_targets,
            "meals_per_day": existing_profile.meals_per_day,
            "meal_schedule": existing_profile.meal_schedule,
            "timezone": existing_profile.timezone,
            "fitness_goals": existing_profile.fitness_goals,
            "initial_assessment": existing_profile.initial_assessment,
            "privacy_settings": existing_profile.privacy_settings,
        })
        db.commit()
        db.refresh(existing_profile)
        return existing_profile
    else:
        # Create new profile
        profile = HealthProfile(user_id=current_user.id, **payload)
        profile.encrypted_data = encrypt_json_payload({
            "age": profile.age,
            "gender": profile.gender,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "occupation_type": profile.occupation_type,
            "activity_level": profile.activity_level,
            "dietary_preferences": profile.dietary_preferences,
            "dietary_restrictions": profile.dietary_restrictions,
            "allergies_intolerances": profile.allergies_intolerances,
            "disliked_ingredients": profile.disliked_ingredients,
            "cuisine_preferences": profile.cuisine_preferences,
            "calorie_target_kcal": profile.calorie_target_kcal,
            "macronutrient_targets": profile.macronutrient_targets,
            "meals_per_day": profile.meals_per_day,
            "meal_schedule": profile.meal_schedule,
            "timezone": profile.timezone,
            "fitness_goals": profile.fitness_goals,
            "initial_assessment": profile.initial_assessment,
            "privacy_settings": profile.privacy_settings,
        })
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile


@router.put("", response_model=HealthProfileResponse)
async def update_health_profile(
    profile_data: HealthProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update health profile."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    
    update_payload = profile_data.model_dump(exclude_unset=True)
    update_payload.pop("height_unit", None)
    update_payload.pop("weight_unit", None)
    if "height_cm" in update_payload and update_payload["height_cm"] is not None:
        update_payload["height_cm"] = normalize_height_to_cm(
            update_payload["height_cm"], profile_data.height_unit or "cm"
        )
    if "weight_kg" in update_payload and update_payload["weight_kg"] is not None:
        update_payload["weight_kg"] = normalize_weight_to_kg(
            update_payload["weight_kg"], profile_data.weight_unit or "kg"
        )
    for key, value in update_payload.items():
        setattr(profile, key, value)

    if profile.activity_level:
        profile.activity_level = standardize_activity_level(profile.activity_level)
    if profile.fitness_goals and profile.fitness_goals.get("target_activity_level"):
        profile.fitness_goals["target_activity_level"] = standardize_activity_level(
            str(profile.fitness_goals["target_activity_level"])
        )
    profile.encrypted_data = encrypt_json_payload({
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "occupation_type": profile.occupation_type,
        "activity_level": profile.activity_level,
        "dietary_preferences": profile.dietary_preferences,
        "dietary_restrictions": profile.dietary_restrictions,
        "allergies_intolerances": profile.allergies_intolerances,
        "disliked_ingredients": profile.disliked_ingredients,
        "cuisine_preferences": profile.cuisine_preferences,
        "calorie_target_kcal": profile.calorie_target_kcal,
        "macronutrient_targets": profile.macronutrient_targets,
        "meals_per_day": profile.meals_per_day,
        "meal_schedule": profile.meal_schedule,
        "timezone": profile.timezone,
        "fitness_goals": profile.fitness_goals,
        "initial_assessment": profile.initial_assessment,
        "privacy_settings": profile.privacy_settings,
    })
    
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete health profile."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if profile:
        db.delete(profile)
        db.commit()
    return None


@router.get("/history")
async def get_profile_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get profile history including creation/update timestamps and metrics history."""
    from ..models.health_metrics import HealthMetrics
    
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    
    # Get all metrics ordered by date
    metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == current_user.id
    ).order_by(HealthMetrics.recorded_at.asc()).all()
    
    # Build history
    history = {
        "profile_created_at": profile.created_at.isoformat() if profile.created_at else None,
        "profile_updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "current_profile": {
            "age": profile.age,
            "gender": profile.gender,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "occupation_type": profile.occupation_type,
            "activity_level": profile.activity_level,
            "dietary_preferences": profile.dietary_preferences,
            "dietary_restrictions": profile.dietary_restrictions,
            "allergies_intolerances": profile.allergies_intolerances,
            "disliked_ingredients": profile.disliked_ingredients,
            "cuisine_preferences": profile.cuisine_preferences,
            "calorie_target_kcal": profile.calorie_target_kcal,
            "macronutrient_targets": profile.macronutrient_targets,
            "meals_per_day": profile.meals_per_day,
            "meal_schedule": profile.meal_schedule,
            "timezone": profile.timezone,
            "fitness_goals": profile.fitness_goals,
            "initial_assessment": profile.initial_assessment,
        },
        "metrics_history": [
            {
                "recorded_at": metric.recorded_at.isoformat() if metric.recorded_at else None,
                "weight_kg": metric.weight_kg,
                "bmi": metric.bmi,
                "wellness_score": metric.wellness_score,
                "activity_frequency": metric.activity_frequency,
                "activity_duration": metric.activity_duration,
                "goal_progress": metric.goal_progress,
            }
            for metric in metrics
        ],
        "total_metrics_records": len(metrics),
    }
    
    return history
