from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..api import get_current_user
from ..database import get_db
from ..models.health_profile import HealthProfile
from ..models.meal_plan import MealPlan, MealPlanVersion
from ..models.user import User
from ..schemas.meal_plan import (
    MealPlanGenerateRequest,
    MealPlanResponse,
    MealSwapRequest,
    MealRegenerateRequest,
    MealManualAddRequest,
    MealReplaceRequest,
    MealPlanVersionResponse,
)
from ..services.meal_plan_service import meal_plan_service

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


def _to_response(plan: MealPlan) -> Dict[str, Any]:
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "duration": plan.duration,
        "target_date": plan.target_date,
        "timezone": plan.timezone,
        "version": plan.version,
        "meals": plan.meals or [],
        "alternatives": plan.alternatives or {},
        "strategy": plan.strategy or {},
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def _save_version(db: Session, plan: MealPlan) -> None:
    version = MealPlanVersion(
        meal_plan_id=plan.id,
        user_id=plan.user_id,
        version=plan.version,
        snapshot={
            "duration": plan.duration,
            "target_date": plan.target_date,
            "timezone": plan.timezone,
            "version": plan.version,
            "meals": plan.meals,
            "alternatives": plan.alternatives,
            "strategy": plan.strategy,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(version)


@router.post("/generate", response_model=MealPlanResponse)
async def generate_meal_plan(
    payload: MealPlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")

    request_data = payload.model_dump(mode="json")
    generated = meal_plan_service.generate_plan(db, profile, request_data)
    version = payload.meal_plan_request.version
    plan = MealPlan(
        user_id=current_user.id,
        duration=payload.meal_plan_request.duration,
        target_date=str(payload.meal_plan_request.date),
        timezone=payload.user_preferences.timezone,
        version=version,
        meals=generated["meals"],
        alternatives=generated["alternatives"],
        strategy={
            "sequential_prompting": generated["prompt_trace"],
            "rag_trace": generated["rag_trace"],
            "strategy": generated["strategy"],
            "structure": generated["structure"],
        },
    )
    db.add(plan)
    db.flush()
    _save_version(db, plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.get("", response_model=List[MealPlanResponse])
async def list_meal_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = (
        db.query(MealPlan)
        .filter(MealPlan.user_id == current_user.id)
        .order_by(MealPlan.created_at.desc())
        .all()
    )
    return [_to_response(plan) for plan in plans]


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")
    return _to_response(plan)


@router.post("/{plan_id}/swap", response_model=MealPlanResponse)
async def swap_meals(
    plan_id: int,
    payload: MealSwapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    meals = list(plan.meals or [])
    src_idx = next((idx for idx, meal in enumerate(meals) if meal.get("id") == payload.source_meal_id), -1)
    tgt_idx = next((idx for idx, meal in enumerate(meals) if meal.get("id") == payload.target_meal_id), -1)
    if src_idx < 0 or tgt_idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both meals not found in plan")

    meals[src_idx], meals[tgt_idx] = meals[tgt_idx], meals[src_idx]
    plan.meals = meals
    plan.version = f"{float(plan.version) + 0.1:.1f}" if plan.version.replace(".", "", 1).isdigit() else "1.1"
    _save_version(db, plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.post("/{plan_id}/manual-add", response_model=MealPlanResponse)
async def manual_add_meal(
    plan_id: int,
    payload: MealManualAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    meals = list(plan.meals or [])
    meals.append(payload.meal.model_dump(mode="json"))
    plan.meals = meals
    plan.version = f"{float(plan.version) + 0.1:.1f}" if plan.version.replace(".", "", 1).isdigit() else "1.1"
    _save_version(db, plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.post("/{plan_id}/replace", response_model=MealPlanResponse)
async def replace_meal(
    plan_id: int,
    payload: MealReplaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    meals = list(plan.meals or [])
    target_idx = next((idx for idx, meal in enumerate(meals) if meal.get("id") == payload.meal_id), -1)
    if target_idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal to replace not found")
    meals[target_idx] = payload.replacement_meal.model_dump(mode="json")
    plan.meals = meals
    plan.version = f"{float(plan.version) + 0.1:.1f}" if plan.version.replace(".", "", 1).isdigit() else "1.1"
    _save_version(db, plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.post("/{plan_id}/regenerate", response_model=MealPlanResponse)
async def regenerate_meal_plan(
    plan_id: int,
    payload: MealRegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not plan or not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan or profile not found")

    request_data = {
        "user_preferences": {
            "dietary_restrictions": profile.dietary_restrictions or [],
            "allergies_intolerances": profile.allergies_intolerances or [],
            "cuisine_preferences": profile.cuisine_preferences or [],
            "disliked_ingredients": profile.disliked_ingredients or [],
            "calorie_target": profile.calorie_target_kcal or 2000,
            "macronutrient_targets": profile.macronutrient_targets or {"protein": 120, "carbs": 200, "fats": 70},
            "meals_per_day": profile.meals_per_day or 3,
            "preferred_meal_times": profile.meal_schedule or {},
            "timezone": profile.timezone or "UTC",
        },
        "meal_plan_request": {
            "duration": plan.duration,
            "date": plan.target_date,
            "version": plan.version,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    generated = meal_plan_service.generate_plan(db, profile, request_data)
    meals = list(plan.meals or [])
    if payload.regenerate_all or not payload.meal_id:
        meals = generated["meals"]
    else:
        replacement = next((m for m in generated["meals"] if m["id"] == payload.meal_id), None)
        if replacement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal to regenerate not found")
        meals = [replacement if m.get("id") == payload.meal_id else m for m in meals]

    plan.meals = meals
    plan.alternatives = generated["alternatives"]
    plan.strategy = generated["strategy"]
    plan.version = f"{float(plan.version) + 0.1:.1f}" if plan.version.replace(".", "", 1).isdigit() else "1.1"
    _save_version(db, plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.get("/{plan_id}/alternatives")
async def get_alternatives(
    plan_id: int,
    meal_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")
    alternatives = (plan.alternatives or {}).get(meal_id, [])
    return {"meal_id": meal_id, "alternatives": alternatives}


@router.get("/{plan_id}/versions", response_model=List[MealPlanVersionResponse])
async def list_versions(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    versions = (
        db.query(MealPlanVersion)
        .filter(MealPlanVersion.meal_plan_id == plan_id, MealPlanVersion.user_id == current_user.id)
        .order_by(MealPlanVersion.created_at.desc())
        .all()
    )
    return versions


@router.post("/{plan_id}/restore/{version_id}", response_model=MealPlanResponse)
async def restore_version(
    plan_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    version = (
        db.query(MealPlanVersion)
        .filter(
            MealPlanVersion.id == version_id,
            MealPlanVersion.meal_plan_id == plan_id,
            MealPlanVersion.user_id == current_user.id,
        )
        .first()
    )
    if not plan or not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan version not found")

    snapshot = version.snapshot or {}
    plan.duration = snapshot.get("duration", plan.duration)
    plan.target_date = snapshot.get("target_date", plan.target_date)
    plan.timezone = snapshot.get("timezone", plan.timezone)
    plan.version = snapshot.get("version", plan.version)
    plan.meals = snapshot.get("meals", plan.meals)
    plan.alternatives = snapshot.get("alternatives", plan.alternatives)
    plan.strategy = snapshot.get("strategy", plan.strategy)
    _save_version(db, plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)
