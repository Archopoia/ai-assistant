from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from openai import OpenAI
from openai import APIConnectionError, APIError, RateLimitError
from sqlalchemy.orm import Session
from ..config import settings
from ..models.health_profile import HealthProfile
from ..models.recipe import Recipe
from .function_calling_service import function_calling_service
from .rag_service import rag_service


class MealPlanService:
    """Sequential meal planning orchestration service."""

    def __init__(self) -> None:
        self.client: Optional[OpenAI] = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _default_meal_times(self, day_start: datetime, meals_per_day: int) -> List[datetime]:
        base_hours = [8, 12, 16, 19, 21]
        slots = base_hours[: max(1, min(meals_per_day, len(base_hours)))]
        return [day_start.replace(hour=hour, minute=0, second=0, microsecond=0) for hour in slots]

    def _build_step1_prompt(self, profile: HealthProfile, request_data: Dict[str, Any]) -> str:
        return (
            "STEP 1 - Analyze user profile and propose a meal strategy in JSON.\n"
            f"Profile: {json.dumps(request_data['user_preferences'], default=str)}\n"
            f"Request: {json.dumps(request_data['meal_plan_request'], default=str)}\n"
            "Return JSON with keys: calorie_distribution, macro_focus, meal_frequency_notes."
        )

    def _build_step2_prompt(self, strategy: Dict[str, Any], request_data: Dict[str, Any]) -> str:
        return (
            "STEP 2 - Based on strategy, create meal structure in JSON.\n"
            f"Strategy: {json.dumps(strategy)}\n"
            f"Request: {json.dumps(request_data['meal_plan_request'], default=str)}\n"
            "Return JSON with keys: day_templates (array), each day has meals with meal_type and goal."
        )

    def _build_step3_prompt(self, structure: Dict[str, Any], augmented_prompt: str) -> str:
        return (
            "STEP 3 - Generate concrete meal suggestions in JSON using retrieved recipe context.\n"
            f"Structure: {json.dumps(structure)}\n"
            f"RAG context: {augmented_prompt}\n"
            "Return JSON with keys: meals (array), alternatives (object)."
        )

    def _model_json(self, prompt: str, temperature: float = 0.2) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Return strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                top_p=0.9,
                max_tokens=1000,
            )
            text = response.choices[0].message.content or "{}"
            if "```json" in text:
                text = text.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in text:
                text = text.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, APIConnectionError, APIError, RateLimitError):
            return None

    def _fallback_strategy(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        prefs = request_data["user_preferences"]
        return {
            "calorie_distribution": "25/35/30 + snacks",
            "macro_focus": prefs.get("macronutrient_targets", {}),
            "meal_frequency_notes": f"{prefs.get('meals_per_day', 3)} meals per day with balanced spread",
        }

    def _fallback_structure(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        duration = request_data["meal_plan_request"].get("duration", "daily")
        day_count = 7 if duration == "weekly" else 1
        meals_per_day = int(request_data["user_preferences"].get("meals_per_day", 3))
        template = []
        meal_labels = ["breakfast", "lunch", "snack", "dinner", "snack"]
        for i in range(meals_per_day):
            template.append({"meal_type": meal_labels[i], "goal": "balanced nutrition"})
        return {"day_templates": [template for _ in range(day_count)]}

    def _pick_recipe_matches(self, db: Session, query: str, count: int = 5) -> List[Recipe]:
        retrieved = rag_service.search_recipes(db, query=query, top_k=count)
        return [item["recipe"] for item in retrieved]

    def _resolve_recipe_from_generated(self, db: Session, generated_meal: Dict[str, Any]) -> Optional[Recipe]:
        recipe_id = generated_meal.get("recipe_id")
        if recipe_id:
            recipe = db.query(Recipe).filter(Recipe.external_id == str(recipe_id)).first()
            if recipe:
                return recipe
        title_candidates = [generated_meal.get("title"), generated_meal.get("name")]
        for candidate in title_candidates:
            if not candidate:
                continue
            recipe = db.query(Recipe).filter(Recipe.title.ilike(f"%{str(candidate).strip()}%")).first()
            if recipe:
                return recipe
        return None

    def generate_plan(
        self,
        db: Session,
        profile: HealthProfile,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        rag_service.ensure_seed_data(db)

        # Sequential prompting step 1: strategy
        step1_prompt = self._build_step1_prompt(profile, request_data)
        strategy = self._model_json(step1_prompt, temperature=0.2) or self._fallback_strategy(request_data)

        # Sequential prompting step 2: structure, grounded in step 1 output
        step2_prompt = self._build_step2_prompt(strategy, request_data)
        structure = self._model_json(step2_prompt, temperature=0.3) or self._fallback_structure(request_data)

        # RAG retrieval and augmentation
        query = " ".join(
            [
                "meal plan",
                " ".join(request_data["user_preferences"].get("cuisine_preferences", [])),
                " ".join(request_data["user_preferences"].get("dietary_restrictions", [])),
            ]
        ).strip()
        retrieved = rag_service.search_recipes(db, query=query or "balanced meals", top_k=10)
        augmented_prompt = rag_service.build_augmented_prompt(query, retrieved)

        # Sequential prompting step 3: concrete meals, grounded in structure + RAG
        step3_prompt = self._build_step3_prompt(structure, augmented_prompt)
        generated = self._model_json(step3_prompt, temperature=0.6) or {}

        duration = request_data["meal_plan_request"]["duration"]
        day_count = 7 if duration == "weekly" else 1
        date_start = datetime.fromisoformat(f"{request_data['meal_plan_request']['date']}T00:00:00+00:00")
        meals_per_day = int(request_data["user_preferences"].get("meals_per_day", 3))
        calorie_target = float(request_data["user_preferences"].get("calorie_target", 2000))
        per_meal_calories = calorie_target / max(meals_per_day, 1)

        assembled_meals: List[Dict[str, Any]] = []
        alternatives: Dict[str, List[Dict[str, Any]]] = {}
        labels = ["breakfast", "lunch", "snack", "dinner", "snack"]
        used_recipe_ids: set[str] = set()
        generated_meals = generated.get("meals") if isinstance(generated, dict) else None
        generated_meals = generated_meals if isinstance(generated_meals, list) else []

        for day_idx in range(day_count):
            day_start = date_start + timedelta(days=day_idx)
            day_times = self._default_meal_times(day_start, meals_per_day)
            for meal_idx in range(meals_per_day):
                meal_type = labels[meal_idx]
                generated_meal = generated_meals[day_idx * meals_per_day + meal_idx] if len(generated_meals) > (day_idx * meals_per_day + meal_idx) else None
                selected: Optional[Recipe] = None
                if isinstance(generated_meal, dict):
                    selected = self._resolve_recipe_from_generated(db, generated_meal)

                pool = self._pick_recipe_matches(db, f"{meal_type} {query} day{day_idx + 1}", count=8)
                unique_pool = [recipe for recipe in pool if recipe.external_id not in used_recipe_ids]
                if not selected:
                    if unique_pool:
                        selected = unique_pool[0]
                    elif pool:
                        selected = pool[0]
                    else:
                        selected = self._pick_recipe_matches(db, f"balanced {meal_type} meal", count=1)[0]
                used_recipe_ids.add(selected.external_id)

                ingredient_payload = selected.ingredients
                nutrition_result = function_calling_service.run_nutrition_tool_call(
                    db=db,
                    ingredients=ingredient_payload,
                    servings=float(selected.servings),
                    user_prompt=f"Calculate nutrition for meal {selected.title}",
                )
                if nutrition_result.get("ok"):
                    nutrition = nutrition_result["result"]["per_serving"]
                else:
                    nutrition = {
                        "calories": round(per_meal_calories, 2),
                        "protein": 25.0,
                        "carbs": 30.0,
                        "fats": 12.0,
                        "micronutrients": {"vitamin_d_mcg": 1.0, "vitamin_b12_mcg": 0.6, "iron_mg": 2.1},
                    }

                meal_id = f"d{day_idx + 1}-m{meal_idx + 1}"
                assembled_meals.append(
                    {
                        "id": meal_id,
                        "name": selected.title,
                        "meal_type": meal_type,
                        "scheduled_at": day_times[meal_idx].isoformat(),
                        "nutrition": nutrition,
                        "recipe_id": selected.external_id,
                        "ingredients": ingredient_payload,
                    }
                )

                alternatives[meal_id] = []
                alternative_pool = [recipe for recipe in pool if recipe.external_id != selected.external_id][:3]
                for alt in alternative_pool:
                    alternatives[meal_id].append(
                        {
                            "id": f"{meal_id}-alt-{alt.external_id}",
                            "name": alt.title,
                            "meal_type": meal_type,
                            "scheduled_at": day_times[meal_idx].isoformat(),
                            "nutrition": alt.nutrition or {},
                            "recipe_id": alt.external_id,
                            "ingredients": alt.ingredients,
                        }
                    )

        plan_payload = {
            "strategy": strategy,
            "structure": structure,
            "generated": generated,
            "meals": assembled_meals,
            "alternatives": alternatives,
            "prompt_trace": [
                {"step": 1, "prompt": step1_prompt, "response": strategy},
                {"step": 2, "prompt": step2_prompt, "response": structure},
                {"step": 3, "prompt": step3_prompt, "response": generated},
            ],
            "rag_trace": {
                "retrieved_recipes": [
                    {"id": item["id"], "title": item["title"], "relevance_score": item["relevance_score"]}
                    for item in retrieved
                ],
                "augmented_prompt": augmented_prompt,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return plan_payload


meal_plan_service = MealPlanService()
