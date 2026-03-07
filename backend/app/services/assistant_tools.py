from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from ..models.health_metrics import HealthMetrics
from ..models.health_profile import HealthProfile
from ..models.meal_plan import MealPlan
from ..models.nutrition_log import NutritionLog
from ..models.recipe import Recipe
from ..models.user import User
from .health_calculator import calculate_bmi, calculate_goal_proximity


class AssistantToolsService:
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_health_metrics",
                    "description": "Retrieve current or historical health metrics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metric_type": {
                                "type": "string",
                                "enum": ["bmi", "weight", "wellness_score", "activity_level", "all"],
                            },
                            "time_period": {
                                "type": "string",
                                "enum": ["current", "weekly", "monthly"],
                                "default": "current",
                            },
                        },
                        "required": ["metric_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_health_goals_and_preferences",
                    "description": "Retrieve health goals, activity targets, and nutrition preferences.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_preferences": {"type": "boolean", "default": True},
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_meal_plan",
                    "description": "Retrieve meal plans for today, tomorrow, or this week.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timeframe": {
                                "type": "string",
                                "enum": ["today", "tomorrow", "week", "latest"],
                                "default": "today",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recipe_for_meal",
                    "description": "Find recipe details and preparation steps for a meal in the plan.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meal_name": {"type": "string"},
                            "day_hint": {"type": "string"},
                        },
                        "required": ["meal_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_nutrition_summary",
                    "description": "Retrieve daily or weekly nutrition summary and target comparison.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period": {
                                "type": "string",
                                "enum": ["daily", "weekly"],
                                "default": "daily",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_chart_data",
                    "description": "Build data payload for wellness charts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chart_kind": {
                                "type": "string",
                                "enum": ["weight_trend", "protein_vs_target", "macro_breakdown"],
                            },
                            "period": {
                                "type": "string",
                                "enum": ["weekly", "monthly", "today"],
                                "default": "monthly",
                            },
                        },
                        "required": ["chart_kind"],
                    },
                },
            },
        ]

    def execute(
        self,
        db: Session,
        current_user: User,
        function_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        supplied_user_id = arguments.get("user_id")
        if supplied_user_id is not None and str(supplied_user_id) != str(current_user.id):
            return {"ok": False, "error": "Unauthorized: cross-user access is not allowed."}
        if function_name == "get_health_metrics":
            return self._get_health_metrics(db, current_user, arguments)
        if function_name == "get_health_goals_and_preferences":
            return self._get_health_goals_and_preferences(db, current_user, arguments)
        if function_name == "get_meal_plan":
            return self._get_meal_plan(db, current_user, arguments)
        if function_name == "get_recipe_for_meal":
            return self._get_recipe_for_meal(db, current_user, arguments)
        if function_name == "get_nutrition_summary":
            return self._get_nutrition_summary(db, current_user, arguments)
        if function_name == "get_chart_data":
            return self._get_chart_data(db, current_user, arguments)
        return {"ok": False, "error": "Unknown function requested."}

    def _get_health_metrics(self, db: Session, current_user: User, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metric_type = str(arguments.get("metric_type", "")).strip().lower()
        time_period = str(arguments.get("time_period", "current")).strip().lower()
        allowed_metrics = {"bmi", "weight", "wellness_score", "activity_level", "all"}
        allowed_periods = {"current", "weekly", "monthly"}
        if metric_type not in allowed_metrics:
            return {"ok": False, "error": "metric_type must be one of bmi, weight, wellness_score, activity_level, all."}
        if time_period not in allowed_periods:
            return {"ok": False, "error": "time_period must be current, weekly, or monthly."}

        profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
        if not profile:
            return {"ok": False, "error": "Health profile not found for this user."}

        days = {"current": 1, "weekly": 7, "monthly": 30}[time_period]
        since = datetime.now(timezone.utc) - timedelta(days=days)
        metrics = (
            db.query(HealthMetrics)
            .filter(HealthMetrics.user_id == current_user.id, HealthMetrics.recorded_at >= since)
            .order_by(HealthMetrics.recorded_at.asc())
            .all()
        )
        latest = (
            db.query(HealthMetrics)
            .filter(HealthMetrics.user_id == current_user.id)
            .order_by(HealthMetrics.recorded_at.desc())
            .first()
        )

        current_weight = float((latest.weight_kg if latest and latest.weight_kg else profile.weight_kg) or 0.0)
        current_height = float(profile.height_cm or 0.0)
        bmi, bmi_class = calculate_bmi(current_weight, current_height) if current_weight and current_height else (None, None)
        wellness_score = float(latest.wellness_score) if latest and latest.wellness_score is not None else None
        activity_level = profile.activity_level

        payload: Dict[str, Any] = {
            "time_period": time_period,
            "data_points": len(metrics),
            "units": {"weight": "kg", "height": "cm"},
            "current": {
                "weight_kg": round(current_weight, 2) if current_weight else None,
                "bmi": bmi,
                "bmi_classification": bmi_class,
                "wellness_score": round(wellness_score, 2) if wellness_score is not None else None,
                "activity_level": activity_level,
            },
            "trend": self._build_metric_trend(metrics),
            "goal_proximity": calculate_goal_proximity(
                current_weight=current_weight or None,
                target_weight=(profile.fitness_goals or {}).get("target_weight"),
                current_activity=activity_level,
                target_activity=(profile.fitness_goals or {}).get("target_activity_level"),
            ),
        }
        if metric_type != "all":
            payload["focus_metric"] = metric_type
        return {"ok": True, "result": payload}

    def _build_metric_trend(self, metrics: List[HealthMetrics]) -> Dict[str, Any]:
        if len(metrics) < 2:
            return {"summary": "Not enough historical points to calculate a trend yet."}
        start = metrics[0]
        end = metrics[-1]
        weight_change = None
        if start.weight_kg is not None and end.weight_kg is not None:
            weight_change = round(float(end.weight_kg) - float(start.weight_kg), 2)
        wellness_change = None
        if start.wellness_score is not None and end.wellness_score is not None:
            wellness_change = round(float(end.wellness_score) - float(start.wellness_score), 2)
        trend_direction = "stable"
        if weight_change is not None:
            if weight_change < -0.2:
                trend_direction = "decreasing"
            elif weight_change > 0.2:
                trend_direction = "increasing"
        return {
            "weight_change_kg": weight_change,
            "wellness_change": wellness_change,
            "trend_direction": trend_direction,
        }

    def _get_health_goals_and_preferences(self, db: Session, current_user: User, arguments: Dict[str, Any]) -> Dict[str, Any]:
        include_preferences = bool(arguments.get("include_preferences", True))
        profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
        if not profile:
            return {"ok": False, "error": "Health profile not found for this user."}
        result: Dict[str, Any] = {
            "name": self._display_name(current_user),
            "activity_level": profile.activity_level,
            "fitness_goals": profile.fitness_goals or {},
            "targets": {
                "calorie_target_kcal": profile.calorie_target_kcal,
                "macronutrient_targets": profile.macronutrient_targets or {},
            },
        }
        if include_preferences:
            result["preferences"] = {
                "dietary_preferences": profile.dietary_preferences or {},
                "dietary_restrictions": profile.dietary_restrictions or {},
                "allergies_intolerances": profile.allergies_intolerances or [],
                "cuisine_preferences": profile.cuisine_preferences or [],
                "disliked_ingredients": profile.disliked_ingredients or [],
            }
        return {"ok": True, "result": result}

    def _get_meal_plan(self, db: Session, current_user: User, arguments: Dict[str, Any]) -> Dict[str, Any]:
        timeframe = str(arguments.get("timeframe", "today")).strip().lower()
        if timeframe not in {"today", "tomorrow", "week", "latest"}:
            return {"ok": False, "error": "timeframe must be one of today, tomorrow, week, latest."}

        today = date.today()
        target_dates = []
        if timeframe == "today":
            target_dates = [today.isoformat()]
        elif timeframe == "tomorrow":
            target_dates = [(today + timedelta(days=1)).isoformat()]
        elif timeframe == "week":
            target_dates = [(today + timedelta(days=i)).isoformat() for i in range(7)]

        plans_q = db.query(MealPlan).filter(MealPlan.user_id == current_user.id)
        if target_dates:
            plans_q = plans_q.filter(MealPlan.target_date.in_(target_dates))
        plans = plans_q.order_by(MealPlan.created_at.desc()).all()
        if not plans and timeframe == "latest":
            plans = (
                db.query(MealPlan)
                .filter(MealPlan.user_id == current_user.id)
                .order_by(MealPlan.created_at.desc())
                .limit(1)
                .all()
            )
        if not plans:
            return {"ok": False, "error": "No meal plan found for the requested timeframe."}

        normalized = []
        for plan in plans[:7]:
            normalized.append(
                {
                    "plan_id": plan.id,
                    "target_date": plan.target_date,
                    "duration": plan.duration,
                    "meals": plan.meals or [],
                }
            )
        return {"ok": True, "result": {"timeframe": timeframe, "plans": normalized}}

    def _get_recipe_for_meal(self, db: Session, current_user: User, arguments: Dict[str, Any]) -> Dict[str, Any]:
        meal_name = str(arguments.get("meal_name", "")).strip().lower()
        day_hint = str(arguments.get("day_hint", "")).strip().lower()
        if not meal_name:
            return {"ok": False, "error": "meal_name is required."}

        plans = (
            db.query(MealPlan)
            .filter(MealPlan.user_id == current_user.id)
            .order_by(MealPlan.created_at.desc())
            .limit(14)
            .all()
        )
        candidate_meal: Optional[Dict[str, Any]] = None
        for plan in plans:
            for meal in plan.meals or []:
                name = str(meal.get("name", "")).lower()
                meal_type = str(meal.get("meal_type", "")).lower()
                scheduled = str(meal.get("scheduled_at", "")).lower()
                if meal_name in {name, meal_type} or meal_name in name:
                    if not day_hint or day_hint in scheduled:
                        candidate_meal = meal
                        break
            if candidate_meal:
                break

        if not candidate_meal:
            return {"ok": False, "error": "Could not find that meal in your current meal plans."}

        recipe_id = candidate_meal.get("recipe_id")
        if recipe_id:
            recipe = db.query(Recipe).filter(Recipe.external_id == str(recipe_id)).first()
            if recipe:
                return {
                    "ok": True,
                    "result": {
                        "meal_name": candidate_meal.get("name"),
                        "recipe_title": recipe.title,
                        "ingredients": recipe.ingredients or [],
                        "preparation": recipe.preparation or [],
                        "nutrition": recipe.nutrition or {},
                    },
                }

        return {
            "ok": True,
            "result": {
                "meal_name": candidate_meal.get("name"),
                "recipe_title": candidate_meal.get("name"),
                "ingredients": candidate_meal.get("ingredients") or [],
                "preparation": [
                    {"step": "Step 1", "description": "Prepare ingredients as listed for this meal.", "ingredients": []},
                    {"step": "Step 2", "description": "Cook based on your standard recipe process.", "ingredients": []},
                ],
                "nutrition": candidate_meal.get("nutrition") or {},
            },
        }

    def _get_nutrition_summary(self, db: Session, current_user: User, arguments: Dict[str, Any]) -> Dict[str, Any]:
        period = str(arguments.get("period", "daily")).strip().lower()
        if period not in {"daily", "weekly"}:
            return {"ok": False, "error": "period must be daily or weekly."}

        profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
        if not profile:
            return {"ok": False, "error": "Health profile not found for this user."}

        today = datetime.now(timezone.utc)
        since = today - timedelta(days=6 if period == "weekly" else 1)
        logs = (
            db.query(NutritionLog)
            .filter(NutritionLog.user_id == current_user.id, NutritionLog.logged_at >= since)
            .order_by(NutritionLog.logged_at.asc())
            .all()
        )
        totals = {"calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fats_g": 0.0}
        for log in logs:
            totals["calories_kcal"] += float(log.calories_kcal or 0.0)
            totals["protein_g"] += float(log.protein_g or 0.0)
            totals["carbs_g"] += float(log.carbs_g or 0.0)
            totals["fats_g"] += float(log.fats_g or 0.0)

        macro_targets = profile.macronutrient_targets or {"protein": 120, "carbs": 220, "fats": 70}
        days = 7 if period == "weekly" else 1
        protein_target_total = float(macro_targets.get("protein", 120.0)) * days
        return {
            "ok": True,
            "result": {
                "period": period,
                "entries": len(logs),
                "totals": {k: round(v, 2) for k, v in totals.items()},
                "targets": {
                    "calorie_target_kcal": float(profile.calorie_target_kcal or 2000.0) * days,
                    "protein_target_g": protein_target_total,
                    "carbs_target_g": float(macro_targets.get("carbs", 220.0)) * days,
                    "fats_target_g": float(macro_targets.get("fats", 70.0)) * days,
                },
                "protein_target_pct": round((totals["protein_g"] / max(protein_target_total, 1.0)) * 100.0, 2),
            },
        }

    def _get_chart_data(self, db: Session, current_user: User, arguments: Dict[str, Any]) -> Dict[str, Any]:
        chart_kind = str(arguments.get("chart_kind", "")).strip().lower()
        period = str(arguments.get("period", "monthly")).strip().lower()
        if chart_kind not in {"weight_trend", "protein_vs_target", "macro_breakdown"}:
            return {"ok": False, "error": "chart_kind must be weight_trend, protein_vs_target, or macro_breakdown."}

        if chart_kind == "weight_trend":
            days = 30 if period == "monthly" else 7
            since = datetime.now(timezone.utc) - timedelta(days=days)
            metrics = (
                db.query(HealthMetrics)
                .filter(HealthMetrics.user_id == current_user.id, HealthMetrics.recorded_at >= since)
                .order_by(HealthMetrics.recorded_at.asc())
                .all()
            )
            data = [
                {"date": item.recorded_at.date().isoformat(), "weight_kg": round(float(item.weight_kg), 2)}
                for item in metrics
                if item.weight_kg is not None
            ]
            if not data:
                return {"ok": False, "error": "No weight data available for this period."}
            return {
                "ok": True,
                "result": {
                    "chart_payload": {
                        "chart_type": "line",
                        "title": "Weight Trend",
                        "description": f"Weight trend for the last {days} days.",
                        "x_key": "date",
                        "y_keys": ["weight_kg"],
                        "data": data,
                    }
                },
            }

        if chart_kind == "protein_vs_target":
            nutrition_summary = self._get_nutrition_summary(db, current_user, {"period": "weekly"})
            if not nutrition_summary.get("ok"):
                return nutrition_summary
            totals = nutrition_summary["result"]["totals"]
            targets = nutrition_summary["result"]["targets"]
            data = [
                {"label": "Protein Intake", "grams": round(float(totals.get("protein_g", 0.0)), 2)},
                {"label": "Protein Target", "grams": round(float(targets.get("protein_target_g", 0.0)), 2)},
            ]
            return {
                "ok": True,
                "result": {
                    "chart_payload": {
                        "chart_type": "bar",
                        "title": "Protein Intake vs Target (Weekly)",
                        "description": "Compare your weekly protein intake against your weekly target.",
                        "x_key": "label",
                        "y_keys": ["grams"],
                        "data": data,
                    }
                },
            }

        nutrition_summary = self._get_nutrition_summary(db, current_user, {"period": "daily"})
        if not nutrition_summary.get("ok"):
            return nutrition_summary
        totals = nutrition_summary["result"]["totals"]
        data = [
            {"macro": "Protein", "grams": round(float(totals.get("protein_g", 0.0)), 2)},
            {"macro": "Carbs", "grams": round(float(totals.get("carbs_g", 0.0)), 2)},
            {"macro": "Fats", "grams": round(float(totals.get("fats_g", 0.0)), 2)},
        ]
        return {
            "ok": True,
            "result": {
                "chart_payload": {
                    "chart_type": "pie",
                    "title": "Macronutrient Breakdown (Today)",
                    "description": "Distribution of your logged macronutrients today.",
                    "x_key": "macro",
                    "y_keys": ["grams"],
                    "data": data,
                }
            },
        }

    def _display_name(self, user: User) -> str:
        # Name is the only user PII intentionally exposed to the assistant.
        email = user.email or "User"
        return email.split("@")[0].replace(".", " ").title()


assistant_tools_service = AssistantToolsService()
