from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from openai import OpenAI
from openai import APIConnectionError, APIError, RateLimitError
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from ..api import get_current_user
from ..config import settings
from ..database import get_db
from ..models.health_profile import HealthProfile
from ..models.nutrition_log import NutritionLog
from ..models.health_metrics import HealthMetrics
from ..models.user import User
from ..schemas.nutrition import (
    NutritionLogCreate,
    NutritionLogResponse,
    NutritionDailySummary,
    NutritionTrendResponse,
)

router = APIRouter(prefix="/nutrition", tags=["nutrition"])

MICRONUTRIENT_RECOMMENDED_DAILY = {
    "vitamin_d_mcg": 15.0,
    "vitamin_b12_mcg": 2.4,
    "iron_mg": 18.0,
}

MICRONUTRIENT_FOOD_SUGGESTIONS = {
    "vitamin_d_mcg": ["salmon", "sardines", "egg yolks", "fortified milk alternatives"],
    "vitamin_b12_mcg": ["eggs", "dairy", "fish", "fortified nutritional yeast"],
    "iron_mg": ["lentils", "spinach", "beans", "lean red meat"],
}


def _daily_totals(logs: List[NutritionLog]) -> Dict[str, float]:
    totals = {"calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fats_g": 0.0}
    for log in logs:
        totals["calories_kcal"] += float(log.calories_kcal or 0.0)
        totals["protein_g"] += float(log.protein_g or 0.0)
        totals["carbs_g"] += float(log.carbs_g or 0.0)
        totals["fats_g"] += float(log.fats_g or 0.0)
    return totals


class NutritionImprovementSuggestions(BaseModel):
    food_recommendations: List[str] = Field(default_factory=list)
    meal_timing_adjustments: List[str] = Field(default_factory=list)
    portion_size_modifications: List[str] = Field(default_factory=list)
    alternative_ingredients: List[str] = Field(default_factory=list)
    weekly_meal_plan_optimizations: List[str] = Field(default_factory=list)
    deficiency_recommendations: List[str] = Field(default_factory=list)
    micronutrient_food_suggestions: Dict[str, List[str]] = Field(default_factory=dict)


class NutritionInsightsPayload(BaseModel):
    highlights: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    macronutrient_balance_analysis: str = ""
    improvement_suggestions: NutritionImprovementSuggestions


def _deterministic_nutrition_insight(weekly: Dict[str, Any]) -> Dict[str, Any]:
    deficits = [point["deficit_surplus_kcal"] for point in weekly["daily_points"]]
    stayed_in_deficit_days = len([d for d in deficits if d < 0])
    severe_deficit_days = len([d for d in deficits if d < -500])
    concern = (
        f"Caloric deficit was more than 500 kcal on {severe_deficit_days} days."
        if severe_deficit_days
        else "No severe caloric deficit days detected."
    )
    latest_micronutrients = weekly.get("latest_micronutrients") or {}
    deficiency_recommendations: List[str] = []
    micronutrient_food_suggestions: Dict[str, List[str]] = {}
    for nutrient, recommended in MICRONUTRIENT_RECOMMENDED_DAILY.items():
        intake = float(latest_micronutrients.get(nutrient, 0.0))
        if intake < recommended:
            nutrient_label = nutrient.replace("_", " ").replace("mcg", "(mcg)").replace("mg", "(mg)")
            deficiency_recommendations.append(
                f"Low {nutrient_label}: {round(intake, 2)} vs {recommended} daily target."
            )
            micronutrient_food_suggestions[nutrient] = MICRONUTRIENT_FOOD_SUGGESTIONS.get(nutrient, [])
    return {
        "highlights": [f"Remained in caloric deficit for {stayed_in_deficit_days} days this week."],
        "concerns": [concern],
        "macronutrient_balance_analysis": "Protein, carbs, and fats are tracked against daily targets.",
        "improvement_suggestions": {
            "food_recommendations": ["Add legumes and leafy greens to improve iron and fiber."],
            "meal_timing_adjustments": ["Keep dinner at least 2 hours before sleep for better consistency."],
            "portion_size_modifications": ["Reduce high-calorie snacks on surplus days."],
            "alternative_ingredients": ["Swap cream sauces for yogurt-based alternatives."],
            "weekly_meal_plan_optimizations": ["Use higher-protein lunches on active days."],
            "deficiency_recommendations": deficiency_recommendations or ["No micronutrient deficiencies detected today."],
            "micronutrient_food_suggestions": micronutrient_food_suggestions,
        },
    }


def _validated_nutrition_insight(payload: Dict[str, Any], weekly: Dict[str, Any]) -> Dict[str, Any]:
    try:
        validated = NutritionInsightsPayload.model_validate(payload)
        return validated.model_dump()
    except ValidationError:
        return _deterministic_nutrition_insight(weekly)


def _ai_nutrition_insight(weekly: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.OPENAI_API_KEY:
        return _deterministic_nutrition_insight(weekly)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = (
        "You are a nutrition analyst. Return strict JSON only.\n"
        "Given weekly daily deficit/surplus values, provide concise nutrition insight with this exact shape:\n"
        "{"
        '"highlights":["..."],'
        '"concerns":["..."],'
        '"macronutrient_balance_analysis":"...",'
        '"improvement_suggestions":{'
        '"food_recommendations":["..."],'
        '"meal_timing_adjustments":["..."],'
        '"portion_size_modifications":["..."],'
        '"alternative_ingredients":["..."],'
        '"weekly_meal_plan_optimizations":["..."],'
        '"deficiency_recommendations":["..."],'
        '"micronutrient_food_suggestions":{"vitamin_d_mcg":["..."],"vitamin_b12_mcg":["..."],"iron_mg":["..."]}'
        "}"
        "}\n"
        f"Weekly data: {json.dumps(weekly)}"
    )
    attempts = max(1, int(settings.AI_RETRY_ATTEMPTS))
    for _ in range(attempts):
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": "Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                top_p=0.9,
                max_tokens=700,
            )
            content = response.choices[0].message.content or "{}"
            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0].strip()
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                continue
            return _validated_nutrition_insight(parsed, weekly)
        except (json.JSONDecodeError, APIConnectionError, APIError, RateLimitError):
            continue
    return _deterministic_nutrition_insight(weekly)


@router.post("/logs", response_model=NutritionLogResponse, status_code=status.HTTP_201_CREATED)
async def create_nutrition_log(
    payload: NutritionLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = NutritionLog(
        user_id=current_user.id,
        meal_plan_id=payload.meal_plan_id,
        meal_label=payload.meal_label,
        logged_at=payload.logged_at,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fats_g=payload.fats_g,
        micronutrients=payload.micronutrients,
    )
    db.add(log)

    # Cross-feature integration: update latest wellness score based on nutrition adherence.
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    latest_metric = (
        db.query(HealthMetrics)
        .filter(HealthMetrics.user_id == current_user.id)
        .order_by(HealthMetrics.recorded_at.desc())
        .first()
    )
    if profile and latest_metric and latest_metric.wellness_score is not None:
        target = float(profile.calorie_target_kcal or 2000.0)
        deviation = abs(float(payload.calories_kcal) - target)
        adherence_bonus = max(-5.0, min(5.0, 5.0 - (deviation / 100.0)))
        latest_metric.wellness_score = max(0.0, min(100.0, round(float(latest_metric.wellness_score) + adherence_bonus, 2)))

    db.commit()
    db.refresh(log)
    return log


@router.get("/logs", response_model=List[NutritionLogResponse])
async def list_nutrition_logs(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    logs = (
        db.query(NutritionLog)
        .filter(NutritionLog.user_id == current_user.id, NutritionLog.logged_at >= start)
        .order_by(NutritionLog.logged_at.desc())
        .all()
    )
    return logs


@router.get("/summary/daily", response_model=NutritionDailySummary)
async def daily_summary(
    target_date: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")

    start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    logs = (
        db.query(NutritionLog)
        .filter(
            NutritionLog.user_id == current_user.id,
            NutritionLog.logged_at >= start_dt,
            NutritionLog.logged_at < end_dt,
        )
        .all()
    )
    totals = _daily_totals(logs)
    micronutrient_totals = {key: 0.0 for key in MICRONUTRIENT_RECOMMENDED_DAILY}
    for log in logs:
        values = log.micronutrients or {}
        for nutrient in micronutrient_totals:
            micronutrient_totals[nutrient] += float(values.get(nutrient, 0.0))
    calorie_target = float(profile.calorie_target_kcal or 2000.0)
    macro_targets = profile.macronutrient_targets or {"protein": 120, "carbs": 220, "fats": 70}
    deficit_surplus = round(totals["calories_kcal"] - calorie_target, 2)
    micronutrient_target_pct = {
        nutrient: round(
            (micronutrient_totals[nutrient] / max(MICRONUTRIENT_RECOMMENDED_DAILY[nutrient], 0.0001)) * 100,
            2,
        )
        for nutrient in MICRONUTRIENT_RECOMMENDED_DAILY
    }

    return {
        "date": target_date,
        "calories_kcal": round(totals["calories_kcal"], 2),
        "protein_g": round(totals["protein_g"], 2),
        "carbs_g": round(totals["carbs_g"], 2),
        "fats_g": round(totals["fats_g"], 2),
        "calorie_target_kcal": calorie_target,
        "deficit_surplus_kcal": deficit_surplus,
        "protein_target_pct": round((totals["protein_g"] / max(float(macro_targets.get("protein", 1)), 1)) * 100, 2),
        "carbs_target_pct": round((totals["carbs_g"] / max(float(macro_targets.get("carbs", 1)), 1)) * 100, 2),
        "fats_target_pct": round((totals["fats_g"] / max(float(macro_targets.get("fats", 1)), 1)) * 100, 2),
        "micronutrients": {key: round(value, 2) for key, value in micronutrient_totals.items()},
        "micronutrient_recommended": MICRONUTRIENT_RECOMMENDED_DAILY,
        "micronutrient_target_pct": micronutrient_target_pct,
    }


@router.get("/summary/weekly")
async def weekly_summary(
    end_date: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    calorie_target = float(profile.calorie_target_kcal or 2000.0)
    start_date = end_date - timedelta(days=6)
    points = []
    deficits: List[float] = []

    for i in range(7):
        day = start_date + timedelta(days=i)
        summary = await daily_summary(day, current_user, db)
        deficits.append(summary["deficit_surplus_kcal"])
        points.append({"date": day.isoformat(), "deficit_surplus_kcal": summary["deficit_surplus_kcal"]})

    avg_calories = round((sum((p["deficit_surplus_kcal"] + calorie_target) for p in points) / 7), 2)
    latest_summary = await daily_summary(end_date, current_user, db)
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_points": points,
        "weekly_average_calories": avg_calories,
        "weekly_average_deficit_surplus": round(sum(deficits) / len(deficits), 2),
        "latest_micronutrients": latest_summary.get("micronutrients", {}),
        "micronutrient_recommended": MICRONUTRIENT_RECOMMENDED_DAILY,
    }


@router.get("/trends", response_model=NutritionTrendResponse)
async def nutrition_trends(
    period: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    days = 7 if period == "weekly" else 30
    end = date.today()
    points = []
    for i in range(days):
        day = end - timedelta(days=(days - i - 1))
        summary = await daily_summary(day, current_user, db)
        points.append({"date": day, "deficit_surplus_kcal": summary["deficit_surplus_kcal"]})
    return {"points": points}


@router.get("/insights")
async def nutrition_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    weekly = await weekly_summary(date.today(), current_user, db)
    return _ai_nutrition_insight(weekly)
