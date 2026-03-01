from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.health_profile import HealthProfile
from ..models.health_metrics import HealthMetrics


def calculate_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    """Calculate BMI and return classification."""
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0, "invalid"
    
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    
    if bmi < 18.5:
        classification = "underweight"
    elif bmi < 25:
        classification = "normal_weight"
    elif bmi < 30:
        classification = "overweight"
    else:
        classification = "obese"
    
    return round(bmi, 2), classification


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to 0-100 scale."""
    if max_val == min_val:
        return 50.0
    normalized = ((value - min_val) / (max_val - min_val)) * 100
    return max(0, min(100, normalized))


def calculate_bmi_score(bmi: float) -> float:
    """Calculate BMI component score (0-100)."""
    # Optimal BMI is around 22-24
    if 18.5 <= bmi <= 24.9:
        return 100.0
    elif bmi < 18.5:
        # Underweight: score decreases as BMI gets further from 18.5
        return normalize_score(bmi, 15, 18.5)
    elif bmi < 30:
        # Overweight: score decreases from 25 to 30
        return normalize_score(bmi, 30, 25)
    else:
        # Obese: score decreases further
        return max(0, normalize_score(bmi, 40, 30))


def calculate_activity_score(activity_level: Optional[str], activity_frequency: Optional[int]) -> float:
    """Calculate activity level component score (0-100)."""
    base_scores = {
        "sedentary": 20,
        "moderate": 60,
        "active": 85,
        "very_active": 100
    }
    
    base_score = base_scores.get(activity_level or "sedentary", 30)
    
    # Adjust based on frequency (0-7 days per week)
    if activity_frequency is not None:
        frequency_bonus = (activity_frequency / 7) * 20
        base_score = min(100, base_score + frequency_bonus)
    
    return base_score


def calculate_progress_score(current_weight: Optional[float], target_weight: Optional[float],
                            current_activity: Optional[str], target_activity: Optional[str]) -> float:
    """Calculate progress toward goals score (0-100)."""
    if not target_weight and not target_activity:
        return 50.0  # No goals set
    
    score_components = []
    
    # Weight progress
    if current_weight and target_weight:
        weight_diff = abs(current_weight - target_weight)
        if weight_diff < 1:
            score_components.append(100)
        elif weight_diff < 5:
            score_components.append(80)
        elif weight_diff < 10:
            score_components.append(60)
        else:
            progress_pct = max(0, 100 - (weight_diff / target_weight * 100))
            score_components.append(progress_pct)
    
    # Activity progress
    activity_levels = ["sedentary", "moderate", "active", "very_active"]
    if current_activity and target_activity:
        try:
            current_idx = activity_levels.index(current_activity.lower())
            target_idx = activity_levels.index(target_activity.lower())
            if current_idx >= target_idx:
                score_components.append(100)
            else:
                progress = (current_idx / target_idx) * 100
                score_components.append(progress)
        except ValueError:
            pass
    
    if not score_components:
        return 50.0
    
    return sum(score_components) / len(score_components)


def calculate_habits_score(activity_frequency: Optional[int], consistency_days: Optional[int] = None) -> float:
    """Calculate health habits score (0-100)."""
    # Base score from frequency
    if activity_frequency is None:
        return 30.0
    
    frequency_score = (activity_frequency / 7) * 70
    
    # Consistency bonus
    consistency_bonus = 0
    if consistency_days:
        if consistency_days >= 30:
            consistency_bonus = 30
        elif consistency_days >= 14:
            consistency_bonus = 20
        elif consistency_days >= 7:
            consistency_bonus = 10
    
    return min(100, frequency_score + consistency_bonus)


def calculate_wellness_score(
    bmi: float,
    activity_level: Optional[str],
    activity_frequency: Optional[int],
    current_weight: Optional[float],
    target_weight: Optional[float],
    current_activity: Optional[str],
    target_activity: Optional[str],
    consistency_days: Optional[int] = None
) -> float:
    """Calculate overall wellness score (0-100)."""
    bmi_score = calculate_bmi_score(bmi)
    activity_score = calculate_activity_score(activity_level, activity_frequency)
    progress_score = calculate_progress_score(current_weight, target_weight, current_activity, target_activity)
    habits_score = calculate_habits_score(activity_frequency, consistency_days)
    
    # Weighted formula
    wellness_score = (
        bmi_score * 0.3 +
        activity_score * 0.3 +
        progress_score * 0.2 +
        habits_score * 0.2
    )
    
    return round(wellness_score, 2)


def calculate_goal_proximity(
    current_weight: Optional[float],
    target_weight: Optional[float],
    current_activity: Optional[str],
    target_activity: Optional[str]
) -> Dict[str, Any]:
    """Calculate proximity to goals."""
    proximity = {}
    
    if current_weight and target_weight:
        weight_diff = target_weight - current_weight
        weight_percentage = (1 - abs(weight_diff) / target_weight) * 100 if target_weight > 0 else 0
        weight_percentage = max(0, min(100, round(weight_percentage, 2)))
        current_milestone = int(weight_percentage // 5) * 5
        next_milestone = min(100, current_milestone + 5)
        proximity["weight"] = {
            "difference_kg": round(weight_diff, 2),
            "progress_percentage": weight_percentage,
            "achieved": abs(weight_diff) < 1,
            "milestone": {
                "current_percent": current_milestone,
                "next_percent": next_milestone
            }
        }
    
    if current_activity and target_activity:
        activity_levels = ["sedentary", "moderate", "active", "very_active"]
        try:
            current_idx = activity_levels.index(current_activity.lower())
            target_idx = activity_levels.index(target_activity.lower())
            activity_progress = (current_idx / target_idx) * 100 if target_idx > 0 else 0
            proximity["activity"] = {
                "current_level": current_activity,
                "target_level": target_activity,
                "progress_percentage": max(0, min(100, round(activity_progress, 2))),
                "achieved": current_idx >= target_idx,
                "milestone": {
                    "current_step": current_idx,
                    "next_step": min(target_idx, current_idx + 1)
                }
            }
        except ValueError:
            pass
    
    return proximity


def get_weekly_progress(db: Session, user_id: int) -> Dict[str, Any]:
    """Get weekly progress comparison."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    recent_metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == user_id,
        HealthMetrics.recorded_at >= week_ago
    ).order_by(HealthMetrics.recorded_at.desc()).all()
    
    if not recent_metrics:
        return {"change": 0, "trend": "no_data"}
    
    latest = recent_metrics[0]
    oldest = recent_metrics[-1]
    
    weight_change = 0
    if latest.weight_kg and oldest.weight_kg:
        weight_change = latest.weight_kg - oldest.weight_kg
    
    wellness_change = 0
    if latest.wellness_score and oldest.wellness_score:
        wellness_change = latest.wellness_score - oldest.wellness_score
    
    return {
        "weight_change_kg": round(weight_change, 2),
        "wellness_change": round(wellness_change, 2),
        "trend": "improving" if wellness_change > 0 else "declining" if wellness_change < 0 else "stable"
    }


def get_monthly_progress(db: Session, user_id: int) -> Dict[str, Any]:
    """Get monthly progress comparison."""
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    
    recent_metrics = db.query(HealthMetrics).filter(
        HealthMetrics.user_id == user_id,
        HealthMetrics.recorded_at >= month_ago
    ).order_by(HealthMetrics.recorded_at.desc()).all()
    
    if not recent_metrics:
        return {"change": 0, "trend": "no_data"}
    
    latest = recent_metrics[0]
    oldest = recent_metrics[-1]
    
    weight_change = 0
    if latest.weight_kg and oldest.weight_kg:
        weight_change = latest.weight_kg - oldest.weight_kg
    
    wellness_change = 0
    if latest.wellness_score and oldest.wellness_score:
        wellness_change = latest.wellness_score - oldest.wellness_score
    
    return {
        "weight_change_kg": round(weight_change, 2),
        "wellness_change": round(wellness_change, 2),
        "trend": "improving" if wellness_change > 0 else "declining" if wellness_change < 0 else "stable"
    }
