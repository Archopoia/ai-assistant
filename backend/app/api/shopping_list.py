from collections import defaultdict
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..api import get_current_user
from ..database import get_db
from ..models.meal_plan import MealPlan
from ..models.ingredient import Ingredient
from ..models.user import User
from ..schemas.shopping_list import ShoppingListResponse, ShoppingListUpdateRequest

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])

SHOPPING_CATEGORY_MAP = {
    "beef": "protein",
    "turkey": "protein",
    "lentil": "protein",
    "beans": "protein",
    "quinoa": "protein",
    "tofu": "protein",
    "chicken": "protein",
    "salmon": "protein",
    "egg": "protein",
    "yogurt": "dairy_and_alternatives",
    "milk": "dairy_and_alternatives",
    "cheese": "dairy_and_alternatives",
    "butter": "dairy_and_alternatives",
    "cream": "dairy_and_alternatives",
    "rice": "grains_and_bakery",
    "bread": "grains_and_bakery",
    "oats": "grains_and_bakery",
    "pasta": "grains_and_bakery",
    "flour": "grains_and_bakery",
    "quinoa": "grains_and_bakery",
    "spinach": "produce",
    "tomato": "produce",
    "apple": "produce",
    "broccoli": "produce",
    "lettuce": "produce",
    "cucumber": "produce",
    "salt": "spices_and_condiments",
    "pepper": "spices_and_condiments",
    "oil": "spices_and_condiments",
    "vinegar": "spices_and_condiments",
    "mustard": "spices_and_condiments",
    "sauce": "spices_and_condiments",
    "kimchi": "frozen",
    "frozen": "frozen",
}

# In-memory per-user shopping list state for quantity/exclusion edits.
_shopping_state: Dict[int, Dict[str, List[Dict]]] = {}


def _categorize(name: str, ingredient_category: str | None = None) -> str:
    if ingredient_category:
        return ingredient_category
    lowered = name.lower()
    for token, category in SHOPPING_CATEGORY_MAP.items():
        if token in lowered:
            return category
    return "produce"


def _aggregate_items(db: Session, meals: List[Dict]) -> List[Dict]:
    grouped = defaultdict(
        lambda: {"quantity": 0.0, "unit": "gram", "category": "produce", "excluded": False, "used_in": set()}
    )
    for meal in meals:
        meal_name = str(meal.get("name") or meal.get("meal_type") or "meal")
        for item in meal.get("ingredients", []) or []:
            name = str(item.get("name", "")).strip().lower()
            if not name:
                continue
            ingredient_category = None
            ingredient_obj = None
            item_id = item.get("id")
            if item_id:
                ingredient_obj = db.query(Ingredient).filter(Ingredient.external_id == str(item_id)).first()
            if ingredient_obj is None:
                ingredient_obj = db.query(Ingredient).filter(Ingredient.label.ilike(name)).first()
            if ingredient_obj is not None:
                ingredient_category = ingredient_obj.category
            grouped[name]["quantity"] += float(item.get("quantity", 0.0))
            grouped[name]["unit"] = item.get("unit", "gram")
            grouped[name]["category"] = _categorize(name, ingredient_category)
            grouped[name]["used_in"].add(meal_name)

    return [
        {
            "name": name,
            "quantity": round(data["quantity"], 2),
            "unit": data["unit"],
            "category": data["category"],
            "excluded": data["excluded"],
            "used_in": sorted(list(data["used_in"])),
        }
        for name, data in grouped.items()
    ]


@router.get("", response_model=ShoppingListResponse)
async def generate_shopping_list(
    plan_id: int = Query(...),
    meal_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    meals = plan.meals or []
    if meal_id:
        meals = [meal for meal in meals if meal.get("id") == meal_id]
        if not meals:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found in plan")

    source = f"meal:{meal_id}" if meal_id else f"plan:{plan_id}"
    items = _aggregate_items(db, meals)
    _shopping_state.setdefault(current_user.id, {})[source] = items
    return {"source": source, "items": items}


@router.put("", response_model=ShoppingListResponse)
async def update_shopping_list(
    source: str = Query(...),
    payload: ShoppingListUpdateRequest = ...,
    current_user: User = Depends(get_current_user),
):
    user_lists = _shopping_state.get(current_user.id, {})
    if source not in user_lists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found")

    items = user_lists[source]
    updates = {item.name.lower(): item for item in payload.items}
    updated_items = []
    for item in items:
        key = item["name"].lower()
        if key in updates:
            update = updates[key]
            item["quantity"] = round(update.quantity, 2)
            item["excluded"] = update.excluded
        updated_items.append(item)

    user_lists[source] = updated_items
    return {"source": source, "items": updated_items}
