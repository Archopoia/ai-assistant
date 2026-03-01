from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database import get_db
from ..api import get_current_user
from ..models.user import User
from ..models.health_profile import HealthProfile
from ..models.health_metrics import HealthMetrics
from ..schemas.health_metrics import HealthMetricsCreate, HealthMetricsResponse
from ..services.health_calculator import (
    calculate_bmi,
    calculate_wellness_score,
    calculate_goal_proximity,
    get_weekly_progress,
    get_monthly_progress
)
from ..services.data_normalizer import standardize_activity_level
from ..services.data_normalizer import normalize_weight_to_kg
from ..services.data_protection import encrypt_json_payload

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/metrics", response_model=HealthMetricsResponse, status_code=status.HTTP_201_CREATED)
async def record_health_metrics(
    metrics_data: HealthMetricsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record new health metrics."""
    recorded_at = metrics_data.recorded_at or datetime.now(timezone.utc)
    existing_metric_same_timestamp = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == current_user.id,
        HealthMetrics.recorded_at == recorded_at
    ).first()
    if existing_metric_same_timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate activity entry for the same timestamp is not allowed"
        )

    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    
    normalized_weight = metrics_data.weight_kg
    if normalized_weight is not None:
        normalized_weight = normalize_weight_to_kg(normalized_weight, metrics_data.weight_unit or "kg")

    # Calculate BMI if weight and height are available
    bmi = None
    bmi_classification = None
    if normalized_weight and profile.height_cm:
        bmi, bmi_classification = calculate_bmi(normalized_weight, profile.height_cm)
    
    # Calculate wellness score
    wellness_score = None
    if profile.weight_kg or normalized_weight:
        weight = normalized_weight or profile.weight_kg
        activity_level = standardize_activity_level(profile.activity_level or "moderate")
        
        # Get goals
        goals = profile.fitness_goals or {}
        target_weight = goals.get("target_weight")
        target_activity = goals.get("target_activity_level")
        if target_activity:
            target_activity = standardize_activity_level(str(target_activity))
        
        wellness_score = calculate_wellness_score(
            bmi=bmi or 0,
            activity_level=activity_level,
            activity_frequency=metrics_data.activity_frequency,
            current_weight=weight,
            target_weight=target_weight,
            current_activity=activity_level,
            target_activity=target_activity
        )
    
    # Calculate goal progress
    goals = profile.fitness_goals or {}
    normalized_target_activity = goals.get("target_activity_level")
    if normalized_target_activity:
        normalized_target_activity = standardize_activity_level(str(normalized_target_activity))
    goal_progress = calculate_goal_proximity(
        current_weight=normalized_weight or profile.weight_kg,
        target_weight=goals.get("target_weight"),
        current_activity=standardize_activity_level(profile.activity_level or "moderate"),
        target_activity=normalized_target_activity
    )
    
    # Create metrics record
    metrics = HealthMetrics(
        user_id=current_user.id,
        recorded_at=recorded_at,
        weight_kg=normalized_weight,
        bmi=bmi,
        wellness_score=wellness_score,
        activity_frequency=metrics_data.activity_frequency,
        activity_duration=metrics_data.activity_duration,
        goal_progress=goal_progress
    )
    metrics.encrypted_data = encrypt_json_payload({
        "weight_kg": metrics.weight_kg,
        "bmi": metrics.bmi,
        "wellness_score": metrics.wellness_score,
        "activity_frequency": metrics.activity_frequency,
        "activity_duration": metrics.activity_duration,
        "goal_progress": metrics.goal_progress,
        "recorded_at": recorded_at.isoformat()
    })
    
    db.add(metrics)
    
    # Update profile with latest weight if provided
    if normalized_weight:
        profile.weight_kg = normalized_weight
    
    db.commit()
    db.refresh(metrics)
    return metrics


@router.get("/metrics", response_model=list[HealthMetricsResponse])
async def get_health_metrics(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get health metrics history."""
    metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == current_user.id
    ).order_by(HealthMetrics.recorded_at.desc()).limit(limit).all()
    return metrics


@router.get("/bmi")
async def get_bmi(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current BMI calculation."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile or not profile.weight_kg or not profile.height_cm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insufficient profile data")
    
    bmi, classification = calculate_bmi(profile.weight_kg, profile.height_cm)
    return {
        "bmi": bmi,
        "classification": classification,
        "weight_kg": profile.weight_kg,
        "height_cm": profile.height_cm
    }


@router.get("/wellness-score")
async def get_wellness_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current wellness score."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    
    # Get latest metrics
    latest_metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == current_user.id
    ).order_by(HealthMetrics.recorded_at.desc()).first()
    
    weight = latest_metrics.weight_kg if latest_metrics else profile.weight_kg
    activity_frequency = latest_metrics.activity_frequency if latest_metrics else None
    
    if not weight or not profile.height_cm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insufficient profile data")
    
    bmi, _ = calculate_bmi(weight, profile.height_cm)
    activity_level = standardize_activity_level(profile.activity_level or "moderate")
    
    goals = profile.fitness_goals or {}
    target_activity = goals.get("target_activity_level")
    if target_activity:
        target_activity = standardize_activity_level(str(target_activity))
    wellness_score = calculate_wellness_score(
        bmi=bmi,
        activity_level=activity_level,
        activity_frequency=activity_frequency,
        current_weight=weight,
        target_weight=goals.get("target_weight"),
        current_activity=activity_level,
        target_activity=target_activity
    )
    
    return {
        "wellness_score": wellness_score,
        "bmi": bmi,
        "activity_level": activity_level
    }


@router.get("/progress/weekly")
async def get_weekly_progress_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get weekly progress."""
    return get_weekly_progress(db, current_user.id)


@router.get("/progress/monthly")
async def get_monthly_progress_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly progress."""
    return get_monthly_progress(db, current_user.id)


@router.get("/goals/proximity")
async def get_goal_proximity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get proximity to goals."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    
    goals = profile.fitness_goals or {}
    target_activity = goals.get("target_activity_level")
    if target_activity:
        target_activity = standardize_activity_level(str(target_activity))
    proximity = calculate_goal_proximity(
        current_weight=profile.weight_kg,
        target_weight=goals.get("target_weight"),
        current_activity=standardize_activity_level(profile.activity_level or "moderate"),
        target_activity=target_activity
    )
    
    return proximity
