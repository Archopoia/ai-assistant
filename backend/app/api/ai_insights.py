from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..api import get_current_user
from ..models.user import User
from ..models.health_profile import HealthProfile
from ..models.health_metrics import HealthMetrics
from ..models.ai_insights import AIInsights
from ..schemas.ai_insights import AIInsightsResponse
from ..services.ai_service import ai_service
from ..services.data_normalizer import prepare_ai_data

router = APIRouter(prefix="/ai-insights", tags=["ai-insights"])


@router.post("/generate/{insight_type}", response_model=AIInsightsResponse)
async def generate_ai_insight(
    insight_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI insight."""
    valid_types = ["health_status", "progress_evaluation", "recommendations", "weekly_summary"]
    if insight_type not in valid_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid insight type")
    
    # Get user profile
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")

    privacy_settings = profile.privacy_settings or {}
    if privacy_settings.get("data_sharing") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI insights are disabled by your privacy settings"
        )
    
    # Get recent metrics
    recent_metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == current_user.id
    ).order_by(HealthMetrics.recorded_at.desc()).limit(10).all()
    
    # Prepare AI data
    goals = profile.fitness_goals or {}
    ai_data = prepare_ai_data(profile, recent_metrics, goals)
    
    # Generate insight
    try:
        import asyncio
        import functools
        # Run in thread pool since OpenAI client is synchronous
        loop = asyncio.get_event_loop()
        insight = await loop.run_in_executor(
            None,
            functools.partial(ai_service.generate_insight, insight_type, ai_data, db, current_user.id)
        )
        
        if not insight:
            cached = db.query(AIInsights).filter(
                AIInsights.user_id == current_user.id,
                AIInsights.insight_type == insight_type
            ).order_by(AIInsights.generated_at.desc()).first()
            if cached:
                return cached
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is currently unavailable. Please try again later."
            )
        
        return insight
    except ValueError as e:
        cached = db.query(AIInsights).filter(
            AIInsights.user_id == current_user.id,
            AIInsights.insight_type == insight_type
        ).order_by(AIInsights.generated_at.desc()).first()
        if cached:
            return cached
        # Handle specific OpenAI errors (quota, rate limit, etc.)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.get("", response_model=list[AIInsightsResponse])
async def get_ai_insights(
    insight_type: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI insights history."""
    query = db.query(AIInsights).filter(AIInsights.user_id == current_user.id)
    
    if insight_type:
        query = query.filter(AIInsights.insight_type == insight_type)
    
    insights = query.order_by(AIInsights.generated_at.desc()).limit(limit).all()
    return insights


@router.get("/latest", response_model=Optional[AIInsightsResponse])
async def get_latest_ai_insight(
    insight_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get latest AI insight."""
    query = db.query(AIInsights).filter(AIInsights.user_id == current_user.id)
    
    if insight_type:
        query = query.filter(AIInsights.insight_type == insight_type)
    
    insight = query.order_by(AIInsights.generated_at.desc()).first()
    return insight
