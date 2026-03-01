from typing import Any, Dict, List, Optional
import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..api import get_current_user
from ..database import get_db
from ..models.ingredient import Ingredient
from ..models.recipe import Recipe
from ..models.user import User
from ..schemas.recipe import (
    RecipeResponse,
    RecipeGenerateRequest,
    RecipeSubstitutionRequest,
    RecipePortionRequest,
)
from ..services.rag_service import rag_service
from ..services.function_calling_service import function_calling_service
from ..services.nutrition_functions import nutrition_functions

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _normalized_ingredient(db: Session, item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(item)
    raw_name = str(normalized.get("name", "")).strip()
    ing_id = normalized.get("id")
    resolved_name = raw_name
    if ing_id:
        ingredient = db.query(Ingredient).filter(Ingredient.external_id == str(ing_id)).first()
        if ingredient and ingredient.label:
            resolved_name = ingredient.label
    if re.match(r"^ingredient[\s_-]?\d+$", resolved_name.lower()):
        fallback = db.query(Ingredient).filter(Ingredient.label.ilike(raw_name)).first()
        if fallback and fallback.label:
            resolved_name = fallback.label
    normalized["name"] = resolved_name
    return normalized


def _build_instructions(meal_type: str, ingredients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not ingredients:
        return []
    ingredient_names = [str(item.get("name", "ingredient")) for item in ingredients]
    proteins = ingredient_names[:2]
    produce = ingredient_names[2:5]
    aromatics = ingredient_names[5:]
    lead = ", ".join(proteins) if proteins else ingredient_names[0]
    sides = ", ".join(produce) if produce else "fresh vegetables"
    finish = ", ".join(aromatics) if aromatics else "herbs and seasoning"
    return [
        {
            "step": "Step 1",
            "description": f"Prep and portion all ingredients. Pat dry {lead} and season lightly with salt and pepper.",
            "ingredients": [item.get("id") for item in ingredients[:2]],
        },
        {
            "step": "Step 2",
            "description": f"Sear {lead} over medium heat until browned and nearly cooked through.",
            "ingredients": [item.get("id") for item in ingredients[:2]],
        },
        {
            "step": "Step 3",
            "description": f"Add {sides} and cook until tender-crisp to keep texture for this {meal_type} dish.",
            "ingredients": [item.get("id") for item in ingredients[2:5]],
        },
        {
            "step": "Step 4",
            "description": f"Stir in {finish}, adjust seasoning, and simmer briefly to bring flavors together.",
            "ingredients": [item.get("id") for item in ingredients[5:]],
        },
        {
            "step": "Step 5",
            "description": "Plate warm and serve immediately.",
            "ingredients": [],
        },
    ]


def _to_recipe_response(recipe: Recipe, db: Optional[Session] = None) -> Dict[str, Any]:
    ingredients = recipe.ingredients or []
    if db is not None:
        ingredients = [_normalized_ingredient(db, item) for item in ingredients]
    preparation = recipe.preparation or []
    repetitive_steps = [
        step for step in preparation if "layer flavors for a" in str(step.get("description", "")).lower()
    ]
    if not preparation or len(repetitive_steps) >= max(1, len(preparation) - 1):
        preparation = _build_instructions(recipe.meal, ingredients)
    return {
        "id": recipe.external_id,
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "meal": recipe.meal,
        "servings": recipe.servings,
        "ingredients": ingredients,
        "summary": recipe.summary,
        "time": recipe.time,
        "difficulty_level": recipe.difficulty_level,
        "dietary_tags": recipe.dietary_tags or [],
        "source": recipe.source,
        "img": recipe.img,
        "preparation": preparation,
        "nutrition": recipe.nutrition or {},
        "created_at": recipe.created_at,
        "updated_at": recipe.updated_at,
    }


@router.get("", response_model=List[RecipeResponse])
async def search_recipes(
    q: Optional[str] = Query(default=None),
    cuisine: Optional[str] = Query(default=None),
    ingredients: Optional[List[str]] = Query(default=None),
    dietary_restrictions: Optional[List[str]] = Query(default=None),
    allergies: Optional[List[str]] = Query(default=None),
    max_calories: Optional[float] = Query(default=None),
    min_protein: Optional[float] = Query(default=None),
    max_prep_time: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user  # consumed by auth dependency
    rag_service.ensure_seed_data(db)

    filters: Dict[str, Any] = {
        "cuisine": cuisine,
        "dietary_restrictions": dietary_restrictions,
        "max_calories": max_calories,
        "max_prep_time": max_prep_time,
    }
    results = rag_service.search_recipes(db, query=q or "recipe", filters=filters, top_k=50)
    recipes = [item["recipe"] for item in results]

    if ingredients:
        ingredient_tokens = {x.lower() for x in ingredients}
        recipes = [
            recipe
            for recipe in recipes
            if ingredient_tokens.issubset({str(i.get("name", "")).lower() for i in (recipe.ingredients or [])})
        ]

    if allergies:
        allergy_tokens = {x.lower().replace(" ", "_") for x in allergies}
        recipes = [recipe for recipe in recipes if allergy_tokens.isdisjoint(set(recipe.dietary_tags or []))]

    if min_protein is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("protein", 0.0)) >= float(min_protein)
        ]

    deduped: List[Recipe] = []
    seen_titles: set[str] = set()
    for recipe in recipes:
        title_key = re.sub(r"\s+", " ", recipe.title.strip().lower())
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(recipe)

    return [_to_recipe_response(recipe, db) for recipe in deduped]


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    rag_service.ensure_seed_data(db)
    recipe = db.query(Recipe).filter(Recipe.external_id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return _to_recipe_response(recipe, db)


@router.post("/generate", response_model=RecipeResponse)
async def generate_recipe(
    payload: RecipeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    rag_service.ensure_seed_data(db)
    retrieved = rag_service.search_recipes(db, query=payload.prompt, top_k=5, filters={"meal": payload.meal})
    if not retrieved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recipes available for generation")

    generated_count = db.query(Recipe).filter(Recipe.source == "rag-custom-generation").count()
    pool = [item["recipe"] for item in retrieved if item["recipe"].source != "rag-custom-generation"]
    if not pool:
        pool = [item["recipe"] for item in retrieved]
    base_recipe: Recipe = pool[generated_count % len(pool)]
    secondary_recipe: Recipe = pool[(generated_count + 1) % len(pool)] if len(pool) > 1 else base_recipe
    new_id = f"rgen{db.query(Recipe).count() + 1:04d}"

    # Blend two retrieved recipes to avoid clone-like output while staying RAG-grounded.
    ingredients: List[Dict[str, Any]] = []
    seen_ing: set[str] = set()
    for item in (base_recipe.ingredients or []) + (secondary_recipe.ingredients or []):
        normalized = _normalized_ingredient(db, item)
        name_key = str(normalized.get("name", "")).strip().lower()
        if not name_key or name_key in seen_ing:
            continue
        ingredients.append(normalized)
        seen_ing.add(name_key)
        if len(ingredients) >= 7:
            break

    prompt_tokens = [token for token in re.findall(r"[a-zA-Z]+", payload.prompt) if len(token) > 2]
    title_hint = " ".join(token.capitalize() for token in prompt_tokens[:2]) or "Chef Special"
    preparation = _build_instructions(payload.meal or base_recipe.meal, ingredients)

    nutrition_result = function_calling_service.run_nutrition_tool_call(
        db=db,
        ingredients=ingredients,
        servings=float(payload.servings),
        user_prompt=payload.prompt,
    )
    nutrition = (
        nutrition_result.get("result", {}).get("per_serving", {})
        if nutrition_result.get("ok")
        else base_recipe.nutrition or {}
    )
    style_words = ["Zesty", "Herbed", "Smoky", "Rustic", "Bright", "Savory"]
    style = style_words[generated_count % len(style_words)]
    main_for_title = str(ingredients[0].get("name", "Signature")).split(" ")[0].title() if ingredients else "Signature"
    recipe_title = (
        f"{payload.cuisine or base_recipe.cuisine} {style} {title_hint} {main_for_title} {payload.meal or base_recipe.meal}"
    ).title()
    recipe = Recipe(
        external_id=new_id,
        title=recipe_title,
        cuisine=payload.cuisine or base_recipe.cuisine,
        meal=payload.meal or base_recipe.meal,
        servings=payload.servings,
        ingredients=ingredients,
        summary=(
            f"Customized from RAG context for '{payload.prompt}' by blending ideas from "
            f"{base_recipe.title} and {secondary_recipe.title}."
        ),
        time=max(15, int((base_recipe.time + secondary_recipe.time) / 2)),
        difficulty_level=base_recipe.difficulty_level,
        dietary_tags=list(set((base_recipe.dietary_tags or []) + (secondary_recipe.dietary_tags or [])))[:5],
        source="rag-custom-generation",
        img=base_recipe.img,
        preparation=preparation,
        nutrition=nutrition,
        embedding=rag_service.create_embedding(f"{payload.prompt} {recipe_title}"),
        rating_avg=base_recipe.rating_avg,
        rating_count=0,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _to_recipe_response(recipe, db)


@router.post("/substitute")
async def substitute_ingredient(
    payload: RecipeSubstitutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    recipe = db.query(Recipe).filter(Recipe.external_id == payload.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    options = rag_service.search_recipes(db, query=f"substitute {payload.ingredient_name}", top_k=10)
    candidate_names: List[str] = []
    for item in options:
        for ing in item["recipe"].ingredients or []:
            name = str(ing.get("name", "")).lower()
            if name != payload.ingredient_name.lower() and name not in candidate_names:
                candidate_names.append(name)
            if len(candidate_names) >= 5:
                break
        if len(candidate_names) >= 5:
            break

    if payload.available_ingredients:
        avail = {x.lower() for x in payload.available_ingredients}
        candidate_names = [name for name in candidate_names if name in avail] or candidate_names

    return {"ingredient": payload.ingredient_name, "substitutions": candidate_names[:5]}


@router.post("/portion")
async def adjust_portion(
    payload: RecipePortionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    recipe = db.query(Recipe).filter(Recipe.external_id == payload.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    scaled_ingredients = nutrition_functions.scale_recipe_ingredients(
        ingredients=recipe.ingredients or [],
        current_servings=float(recipe.servings),
        target_servings=float(payload.servings),
    )
    nutrition_result = function_calling_service.run_nutrition_tool_call(
        db=db,
        ingredients=scaled_ingredients,
        servings=float(payload.servings),
        user_prompt=f"Recalculate nutrition for {recipe.title}",
    )
    if not nutrition_result.get("ok"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=nutrition_result.get("message"))

    recipe.servings = payload.servings
    recipe.ingredients = scaled_ingredients
    recipe.nutrition = nutrition_result["result"]["per_serving"]
    db.commit()
    db.refresh(recipe)

    return {"recipe": _to_recipe_response(recipe, db), "function_calling_result": nutrition_result}


@router.post("/{recipe_id}/rate")
async def rate_recipe(
    recipe_id: str,
    rating: float = Query(ge=1, le=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    recipe = db.query(Recipe).filter(Recipe.external_id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    current_avg = float(recipe.rating_avg or 0.0)
    current_count = int(recipe.rating_count or 0)
    new_count = current_count + 1
    recipe.rating_avg = round(((current_avg * current_count) + rating) / new_count, 2)
    recipe.rating_count = new_count
    db.commit()
    return {"recipe_id": recipe_id, "rating_avg": recipe.rating_avg, "rating_count": recipe.rating_count}
