from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from ..database import get_db
from ..api import get_current_user
from ..models.user import User
from ..models.health_profile import HealthProfile
from ..models.health_metrics import HealthMetrics
from ..models.ai_insights import AIInsights
from ..schemas.user import UserResponse, UserUpdate
from ..utils.security import get_password_hash
from ..utils.validators import validate_email, validate_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    if user_update.email and user_update.email != current_user.email:
        if not validate_email(user_update.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
        
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        
        current_user.email = user_update.email
        current_user.email_verified = False
    
    if user_update.password:
        is_valid, error_msg = validate_password(user_update.password)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg or "Invalid password")
        current_user.password_hash = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all user data including profile, metrics, and AI insights (GDPR requirement)."""
    # Get user profile
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    
    # Get all health metrics
    metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == current_user.id
    ).order_by(HealthMetrics.recorded_at.desc()).all()
    
    # Get all AI insights
    insights = db.query(AIInsights).filter(
        AIInsights.user_id == current_user.id
    ).order_by(AIInsights.generated_at.desc()).all()
    
    # Build export data
    export_data: Dict[str, Any] = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "email_verified": current_user.email_verified,
            "two_factor_enabled": current_user.two_factor_enabled,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
        },
        "health_profile": None,
        "health_metrics": [],
        "ai_insights": []
    }
    
    if profile:
        export_data["health_profile"] = {
            "id": profile.id,
            "age": profile.age,
            "gender": profile.gender,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "occupation_type": profile.occupation_type,
            "activity_level": profile.activity_level,
            "dietary_preferences": profile.dietary_preferences,
            "dietary_restrictions": profile.dietary_restrictions,
            "fitness_goals": profile.fitness_goals,
            "initial_assessment": profile.initial_assessment,
            "privacy_settings": profile.privacy_settings,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
    
    for metric in metrics:
        export_data["health_metrics"].append({
            "id": metric.id,
            "recorded_at": metric.recorded_at.isoformat() if metric.recorded_at else None,
            "weight_kg": metric.weight_kg,
            "bmi": metric.bmi,
            "wellness_score": metric.wellness_score,
            "activity_frequency": metric.activity_frequency,
            "activity_duration": metric.activity_duration,
            "goal_progress": metric.goal_progress,
        })
    
    for insight in insights:
        export_data["ai_insights"].append({
            "id": insight.id,
            "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
            "insight_type": insight.insight_type,
            "content": insight.content,
            "version": insight.version,
            "context_snapshot": insight.context_snapshot,
        })
    
    return JSONResponse(content=export_data)
