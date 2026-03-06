from __future__ import annotations

import time
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from ..models.ingredient import Ingredient


class NutritionFunctionError(Exception):
    pass


class NutritionValidationError(NutritionFunctionError):
    pass


class NutritionTimeoutError(NutritionFunctionError):
    pass


class NutritionFunctions:
    """Nutrition computation functions exposed to AI/function-calling orchestration."""

    MAX_EXECUTION_SECONDS = 5.0

    def _validate_ingredients(self, ingredients: Any, servings: Any) -> None:
        if not isinstance(ingredients, list) or not ingredients:
            raise NutritionValidationError("ingredients must be a non-empty array")
        if not isinstance(servings, (int, float)) or float(servings) <= 0:
            raise NutritionValidationError("servings must be a positive number")
        for item in ingredients:
            if not isinstance(item, dict):
                raise NutritionValidationError("ingredient items must be objects")
            for field in ("name", "quantity"):
                if field not in item:
                    raise NutritionValidationError(f"ingredient is missing required field: {field}")
            if float(item["quantity"]) <= 0:
                raise NutritionValidationError("ingredient.quantity must be > 0")

    def calculate_nutrition(self, db: Session, ingredients: List[Dict[str, Any]], servings: float) -> Dict[str, Any]:
        start = time.monotonic()
        self._validate_ingredients(ingredients, servings)

        totals = {
            "calories": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fats": 0.0,
            "fiber_g": 0.0,
            "sugar_g": 0.0,
            "sodium_mg": 0.0,
            "micronutrients": {"vitamin_d_mcg": 0.0, "vitamin_b12_mcg": 0.0, "iron_mg": 0.0},
            "missing_ingredients": [],
        }

        for item in ingredients:
            if time.monotonic() - start > self.MAX_EXECUTION_SECONDS:
                raise NutritionTimeoutError("nutrition function execution timed out")

            name = str(item.get("name", "")).strip().lower()
            quantity = float(item.get("quantity", 0))
            unit = str(item.get("unit", "gram")).lower()

            ingredient = db.query(Ingredient).filter(Ingredient.label.ilike(name)).first()
            if ingredient is None:
                ingredient = db.query(Ingredient).filter(Ingredient.external_id == name).first()
            if ingredient is None:
                totals["missing_ingredients"].append(name)
                continue

            base_quantity = float(ingredient.quantity or 100.0)
            if unit == "ml" and ingredient.unit == "gram":
                # Keep deterministic conversion if unit mismatch appears.
                quantity = quantity * 1.0
            scale = quantity / base_quantity
            nutrition = ingredient.nutrition or {}

            totals["calories"] += float(nutrition.get("calories", 0.0)) * scale
            totals["protein"] += float(nutrition.get("protein", 0.0)) * scale
            totals["carbs"] += float(nutrition.get("carbs", 0.0)) * scale
            totals["fats"] += float(nutrition.get("fats", 0.0)) * scale
            totals["fiber_g"] += float(nutrition.get("fiber_g", 0.0)) * scale
            totals["sugar_g"] += float(nutrition.get("sugar_g", 0.0)) * scale
            totals["sodium_mg"] += float(nutrition.get("sodium_mg", 0.0)) * scale
            totals["micronutrients"]["vitamin_d_mcg"] += float(nutrition.get("vitamin_d_mcg", 0.0)) * scale
            totals["micronutrients"]["vitamin_b12_mcg"] += float(nutrition.get("vitamin_b12_mcg", 0.0)) * scale
            totals["micronutrients"]["iron_mg"] += float(nutrition.get("iron_mg", 0.0)) * scale

        if time.monotonic() - start > self.MAX_EXECUTION_SECONDS:
            raise NutritionTimeoutError("nutrition function execution timed out")

        per_serving = {
            "calories": round(totals["calories"] / servings, 2),
            "protein": round(totals["protein"] / servings, 2),
            "carbs": round(totals["carbs"] / servings, 2),
            "fats": round(totals["fats"] / servings, 2),
            "fiber_g": round(totals["fiber_g"] / servings, 2),
            "sugar_g": round(totals["sugar_g"] / servings, 2),
            "sodium_mg": round(totals["sodium_mg"] / servings, 2),
            "micronutrients": {
                "vitamin_d_mcg": round(totals["micronutrients"]["vitamin_d_mcg"] / servings, 2),
                "vitamin_b12_mcg": round(totals["micronutrients"]["vitamin_b12_mcg"] / servings, 2),
                "iron_mg": round(totals["micronutrients"]["iron_mg"] / servings, 2),
            },
        }

        return {
            "totals": {
                "calories": round(totals["calories"], 2),
                "protein": round(totals["protein"], 2),
                "carbs": round(totals["carbs"], 2),
                "fats": round(totals["fats"], 2),
                "fiber_g": round(totals["fiber_g"], 2),
                "sugar_g": round(totals["sugar_g"], 2),
                "sodium_mg": round(totals["sodium_mg"], 2),
            },
            "per_serving": per_serving,
            "missing_ingredients": totals["missing_ingredients"],
        }

    def scale_recipe_ingredients(
        self, ingredients: List[Dict[str, Any]], current_servings: float, target_servings: float
    ) -> List[Dict[str, Any]]:
        if current_servings <= 0 or target_servings <= 0:
            raise NutritionValidationError("serving values must be positive")
        factor = target_servings / current_servings
        scaled: List[Dict[str, Any]] = []
        for item in ingredients:
            scaled.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "quantity": round(float(item.get("quantity", 0)) * factor, 2),
                    "unit": item.get("unit", "gram"),
                }
            )
        return scaled


nutrition_functions = NutritionFunctions()
