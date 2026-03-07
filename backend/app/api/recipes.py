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

VERIFIED_MIN_RATING = 4.5
VERIFIED_MIN_COUNT = 5
MODERATION_PENDING = "pending"
MODERATION_APPROVED = "approved"
MODERATION_FLAGGED = "flagged"
MODERATION_REJECTED = "rejected"


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


def _derived_schema_additions(nutrition: Dict[str, Any]) -> Dict[str, Any]:
    carbs = float(nutrition.get("carbs", 0.0))
    fiber = float(nutrition.get("fiber_g", 0.0))
    protein = float(nutrition.get("protein", 0.0))
    fats = float(nutrition.get("fats", 0.0))
    calories = float(nutrition.get("calories", 0.0))
    sodium = float(nutrition.get("sodium_mg", 0.0))
    micronutrients = nutrition.get("micronutrients") or {}
    micronutrient_sum = (
        float(micronutrients.get("vitamin_d_mcg", 0.0))
        + float(micronutrients.get("vitamin_b12_mcg", 0.0))
        + float(micronutrients.get("iron_mg", 0.0))
    )
    gi = int(max(20, min(90, 55 + (carbs * 0.15) - (fiber * 0.5))))
    nutrient_density_score = round(max(1.0, min(10.0, ((protein + fiber + micronutrient_sum) / max(calories, 100.0)) * 120)), 2)
    processing_level = "minimally processed" if sodium < 400 else "processed"
    satiety_index = int(max(20, min(100, 35 + (protein * 0.5) + (fiber * 1.2) + (fats * 0.25))))
    antioxidant_profile = {
        "polyphenols": "high" if fiber >= 8 else "medium" if fiber >= 4 else "low",
        "flavonoids": "high" if micronutrient_sum >= 12 else "medium" if micronutrient_sum >= 5 else "low",
        "carotenoids": "high" if float(micronutrients.get("vitamin_d_mcg", 0.0)) >= 3 else "medium" if float(micronutrients.get("vitamin_d_mcg", 0.0)) >= 1 else "low",
    }
    environmental_impact = {
        "carbon_footprint": "high" if protein > 35 else "medium" if protein > 20 else "low",
        "water_usage": "high" if calories > 700 else "medium" if calories > 450 else "low",
    }
    return {
        "glycemic_index": gi,
        "antioxidant_profile": antioxidant_profile,
        "nutrient_density_score": nutrient_density_score,
        "processing_level": processing_level,
        "environmental_impact": environmental_impact,
        "satiety_index": satiety_index,
    }


def _normalized_nutrition(recipe: Recipe) -> Dict[str, Any]:
    nutrition = dict(recipe.nutrition or {})
    nutrition.setdefault("calories", 0.0)
    nutrition.setdefault("protein", 0.0)
    nutrition.setdefault("carbs", 0.0)
    nutrition.setdefault("fats", 0.0)
    nutrition.setdefault("fiber_g", 0.0)
    nutrition.setdefault("sugar_g", 0.0)
    nutrition.setdefault("sodium_mg", 0.0)
    micros = dict(nutrition.get("micronutrients") or {})
    micros.setdefault("vitamin_d_mcg", 0.0)
    micros.setdefault("vitamin_b12_mcg", 0.0)
    micros.setdefault("iron_mg", 0.0)
    nutrition["micronutrients"] = micros
    feedback = dict(nutrition.get("community_feedback") or {})
    if "moderation_status" not in feedback:
        feedback["moderation_status"] = MODERATION_PENDING if recipe.source == "rag-custom-generation" else MODERATION_APPROVED
    feedback.setdefault("moderation_note", None)
    feedback.setdefault("verified_recommendation", False)
    nutrition["community_feedback"] = feedback
    derived = _derived_schema_additions(nutrition)
    nutrition.setdefault("glycemic_index", derived["glycemic_index"])
    nutrition.setdefault("antioxidant_profile", derived["antioxidant_profile"])
    nutrition.setdefault("nutrient_density_score", derived["nutrient_density_score"])
    nutrition.setdefault("processing_level", derived["processing_level"])
    nutrition.setdefault("environmental_impact", derived["environmental_impact"])
    nutrition.setdefault("satiety_index", derived["satiety_index"])
    return nutrition


def _is_verified_recipe(recipe: Recipe, nutrition: Dict[str, Any]) -> bool:
    status = str((nutrition.get("community_feedback") or {}).get("moderation_status", MODERATION_APPROVED)).lower()
    if status in {MODERATION_REJECTED, MODERATION_FLAGGED, MODERATION_PENDING}:
        return False
    return float(recipe.rating_avg or 0.0) >= VERIFIED_MIN_RATING and int(recipe.rating_count or 0) >= VERIFIED_MIN_COUNT


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
    nutrition = _normalized_nutrition(recipe)
    is_verified = _is_verified_recipe(recipe, nutrition)
    feedback = nutrition.get("community_feedback") or {}
    feedback["verified_recommendation"] = is_verified
    nutrition["community_feedback"] = feedback
    recipe.nutrition = nutrition
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
        "nutrition": nutrition,
        "rating_avg": float(recipe.rating_avg or 0.0),
        "rating_count": int(recipe.rating_count or 0),
        "moderation_status": str((nutrition.get("community_feedback") or {}).get("moderation_status", MODERATION_APPROVED)),
        "is_verified": is_verified,
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
    max_protein: Optional[float] = Query(default=None),
    min_carbs: Optional[float] = Query(default=None),
    max_carbs: Optional[float] = Query(default=None),
    min_fats: Optional[float] = Query(default=None),
    max_fats: Optional[float] = Query(default=None),
    max_prep_time: Optional[int] = Query(default=None),
    min_vitamin_d_mcg: Optional[float] = Query(default=None),
    max_vitamin_d_mcg: Optional[float] = Query(default=None),
    min_vitamin_b12_mcg: Optional[float] = Query(default=None),
    max_vitamin_b12_mcg: Optional[float] = Query(default=None),
    min_iron_mg: Optional[float] = Query(default=None),
    max_iron_mg: Optional[float] = Query(default=None),
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
    recipes = [
        recipe
        for recipe in recipes
        if str((_normalized_nutrition(recipe).get("community_feedback") or {}).get("moderation_status", MODERATION_APPROVED)).lower()
        != MODERATION_REJECTED
    ]

    if min_protein is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("protein", 0.0)) >= float(min_protein)
        ]
    if max_protein is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("protein", 0.0)) <= float(max_protein)
        ]
    if min_carbs is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("carbs", 0.0)) >= float(min_carbs)
        ]
    if max_carbs is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("carbs", 0.0)) <= float(max_carbs)
        ]
    if min_fats is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("fats", 0.0)) >= float(min_fats)
        ]
    if max_fats is not None:
        recipes = [
            recipe for recipe in recipes if float((recipe.nutrition or {}).get("fats", 0.0)) <= float(max_fats)
        ]
    if min_vitamin_d_mcg is not None:
        recipes = [
            recipe
            for recipe in recipes
            if float(((recipe.nutrition or {}).get("micronutrients") or {}).get("vitamin_d_mcg", 0.0))
            >= float(min_vitamin_d_mcg)
        ]
    if max_vitamin_d_mcg is not None:
        recipes = [
            recipe
            for recipe in recipes
            if float(((recipe.nutrition or {}).get("micronutrients") or {}).get("vitamin_d_mcg", 0.0))
            <= float(max_vitamin_d_mcg)
        ]
    if min_vitamin_b12_mcg is not None:
        recipes = [
            recipe
            for recipe in recipes
            if float(((recipe.nutrition or {}).get("micronutrients") or {}).get("vitamin_b12_mcg", 0.0))
            >= float(min_vitamin_b12_mcg)
        ]
    if max_vitamin_b12_mcg is not None:
        recipes = [
            recipe
            for recipe in recipes
            if float(((recipe.nutrition or {}).get("micronutrients") or {}).get("vitamin_b12_mcg", 0.0))
            <= float(max_vitamin_b12_mcg)
        ]
    if min_iron_mg is not None:
        recipes = [
            recipe
            for recipe in recipes
            if float(((recipe.nutrition or {}).get("micronutrients") or {}).get("iron_mg", 0.0))
            >= float(min_iron_mg)
        ]
    if max_iron_mg is not None:
        recipes = [
            recipe
            for recipe in recipes
            if float(((recipe.nutrition or {}).get("micronutrients") or {}).get("iron_mg", 0.0))
            <= float(max_iron_mg)
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


@router.get("/recommendations/verified", response_model=List[RecipeResponse])
async def verified_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    rag_service.ensure_seed_data(db)
    recipes = (
        db.query(Recipe)
        .filter(Recipe.rating_avg.isnot(None))
        .order_by(Recipe.rating_avg.desc(), Recipe.rating_count.desc())
        .limit(max(limit * 3, limit))
        .all()
    )
    verified = []
    for recipe in recipes:
        nutrition = _normalized_nutrition(recipe)
        if _is_verified_recipe(recipe, nutrition):
            verified.append(recipe)
        if len(verified) >= limit:
            break
    return [_to_recipe_response(recipe, db) for recipe in verified]


@router.get("/moderation/queue", response_model=List[RecipeResponse])
async def moderation_queue(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    rag_service.ensure_seed_data(db)
    candidates = (
        db.query(Recipe)
        .filter(Recipe.source == "rag-custom-generation")
        .order_by(Recipe.updated_at.desc(), Recipe.created_at.desc())
        .limit(max(limit * 4, limit))
        .all()
    )
    queued: List[Recipe] = []
    for recipe in candidates:
        status = str((_normalized_nutrition(recipe).get("community_feedback") or {}).get("moderation_status", "")).lower()
        if status in {MODERATION_PENDING, MODERATION_FLAGGED}:
            queued.append(recipe)
        if len(queued) >= limit:
            break
    return [_to_recipe_response(recipe, db) for recipe in queued]


@router.post("/{recipe_id}/moderate")
async def moderate_recipe(
    recipe_id: str,
    action: str = Query(pattern="^(approve|reject|flag)$"),
    note: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    recipe = db.query(Recipe).filter(Recipe.external_id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    nutrition = _normalized_nutrition(recipe)
    feedback = dict(nutrition.get("community_feedback") or {})
    normalized_action = action.lower().strip()
    status_map = {
        "approve": MODERATION_APPROVED,
        "reject": MODERATION_REJECTED,
        "flag": MODERATION_FLAGGED,
    }
    feedback["moderation_status"] = status_map[normalized_action]
    feedback["moderation_note"] = note
    nutrition["community_feedback"] = feedback
    recipe.nutrition = nutrition
    db.commit()
    db.refresh(recipe)
    return {
        "recipe_id": recipe.external_id,
        "moderation_status": feedback["moderation_status"],
        "moderation_note": feedback.get("moderation_note"),
    }


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
    if not nutrition_result.get("ok"):
        nutrition_result = function_calling_service.safe_execute(
            db=db,
            function_name="calculate_nutrition",
            arguments={"ingredients": ingredients, "servings": float(payload.servings)},
        )
    if not nutrition_result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=nutrition_result.get("message") or "Unable to calculate recipe nutrition",
        )
    nutrition = nutrition_result.get("result", {}).get("per_serving", {})
    nutrition.setdefault("fiber_g", 0.0)
    nutrition.setdefault("sugar_g", 0.0)
    nutrition.setdefault("sodium_mg", 0.0)
    nutrition.setdefault("micronutrients", {"vitamin_d_mcg": 0.0, "vitamin_b12_mcg": 0.0, "iron_mg": 0.0})
    nutrition.update(_derived_schema_additions(nutrition))
    nutrition["community_feedback"] = {
        "moderation_status": MODERATION_PENDING,
        "moderation_note": "Awaiting moderation review.",
        "verified_recommendation": False,
    }
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
    nutrition = _normalized_nutrition(recipe)
    feedback = dict(nutrition.get("community_feedback") or {})
    if rating <= 2 and new_count >= 3:
        feedback["moderation_status"] = MODERATION_FLAGGED
        feedback["moderation_note"] = "Auto-flagged due to repeated low ratings."
    if feedback.get("moderation_status") == MODERATION_APPROVED:
        feedback["verified_recommendation"] = _is_verified_recipe(recipe, nutrition)
    else:
        feedback["verified_recommendation"] = False
    nutrition["community_feedback"] = feedback
    recipe.nutrition = nutrition
    db.commit()
    return {
        "recipe_id": recipe_id,
        "rating_avg": recipe.rating_avg,
        "rating_count": recipe.rating_count,
        "moderation_status": feedback.get("moderation_status", MODERATION_APPROVED),
        "verified_recommendation": feedback.get("verified_recommendation", False),
    }
