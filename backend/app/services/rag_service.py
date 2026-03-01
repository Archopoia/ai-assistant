import hashlib
import math
import random
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from ..models.ingredient import Ingredient
from ..models.recipe import Recipe


class RAGService:
    """Recipe and ingredient retrieval service with lightweight local embeddings."""

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions
        self.seed_value = 20260301
        self.cuisines = [
            "Italian", "Mexican", "Mediterranean", "Indian", "Japanese",
            "Thai", "American", "French", "Korean", "Middle Eastern",
        ]
        self.meal_types = ["breakfast", "lunch", "dinner", "snack"]
        self.categories = [
            "produce", "protein", "dairy_and_alternatives",
            "grains_and_bakery", "spices_and_condiments", "frozen",
        ]
        self.dietary_tags = [
            "vegetarian", "vegan", "pescatarian", "keto", "paleo",
            "mediterranean", "low_carb", "high_protein", "dash", "gluten_free",
            "dairy_free", "halal", "kosher", "whole30", "plant_based",
        ]
        self.recipe_title_templates = [
            "{cuisine} {meal} featuring {main}",
            "{cuisine}-style {main} {meal}",
            "{main} {cuisine} {meal} plate",
            "{cuisine} {meal} with {main} and herbs",
            "{main} and seasonal vegetables ({cuisine} {meal})",
        ]
        self.base_ingredient_names = [
            "chicken breast", "chicken thigh", "ground turkey", "lean beef", "salmon fillet", "tuna",
            "shrimp", "tofu", "tempeh", "chickpeas", "black beans", "kidney beans", "lentils",
            "quinoa", "brown rice", "wild rice", "rolled oats", "barley", "whole wheat pasta",
            "sourdough bread", "spinach", "kale", "broccoli", "cauliflower", "carrot", "zucchini",
            "cucumber", "cherry tomatoes", "bell pepper", "red onion", "garlic", "ginger", "mushrooms",
            "eggplant", "sweet potato", "potato", "green beans", "peas", "corn", "avocado", "apple",
            "banana", "blueberries", "strawberries", "orange", "lemon", "lime", "feta cheese",
            "greek yogurt", "cottage cheese", "parmesan", "mozzarella", "milk", "oat milk", "almond milk",
            "olive oil", "sesame oil", "canola oil", "coconut oil", "butter", "ghee", "soy sauce",
            "tamari", "balsamic vinegar", "apple cider vinegar", "mustard", "hummus", "tahini",
            "peanut butter", "almond butter", "walnuts", "almonds", "cashews", "chia seeds",
            "flax seeds", "sunflower seeds", "pumpkin seeds", "basil", "oregano", "thyme",
            "rosemary", "parsley", "cilantro", "cumin", "paprika", "turmeric", "cinnamon", "black pepper",
            "sea salt", "honey", "maple syrup", "cocoa powder", "dark chocolate", "eggs", "egg whites",
            "plain yogurt", "ricotta", "chicken stock", "vegetable broth", "tomato paste", "crushed tomatoes",
            "coconut milk", "red lentil pasta", "buckwheat noodles", "farro", "bulgur", "edamame",
            "artichoke hearts", "sun-dried tomatoes", "arugula", "romaine lettuce", "mixed greens",
            "beetroot", "radish", "celery", "scallions", "jalapeno", "poblano pepper", "kimchi", "miso",
            "seaweed", "sardines", "cod fillet", "whole grain tortilla", "pita bread", "naan",
        ]
        self.name_prefixes = ["", "fresh ", "organic ", "seasonal ", "locally sourced "]

    def _tokenize(self, text: str) -> List[str]:
        return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token]

    def _build_realistic_ingredient_names(self, min_items: int) -> List[str]:
        names: List[str] = []
        for prefix in self.name_prefixes:
            for base in self.base_ingredient_names:
                label = f"{prefix}{base}".strip()
                if label not in names:
                    names.append(label)
                if len(names) >= min_items:
                    return names
        counter = 1
        while len(names) < min_items:
            base = self.base_ingredient_names[counter % len(self.base_ingredient_names)]
            names.append(f"{base} blend {counter}")
            counter += 1
        return names

    def _infer_category(self, label: str) -> str:
        text = label.lower()
        if any(t in text for t in ["chicken", "beef", "salmon", "shrimp", "tofu", "tempeh", "lentils", "beans", "tuna", "egg"]):
            return "protein"
        if any(t in text for t in ["milk", "cheese", "yogurt", "ricotta", "feta", "parmesan", "mozzarella"]):
            return "dairy_and_alternatives"
        if any(t in text for t in ["rice", "oats", "pasta", "bread", "farro", "bulgur", "barley", "tortilla", "naan", "pita"]):
            return "grains_and_bakery"
        if any(t in text for t in ["salt", "pepper", "paprika", "cumin", "turmeric", "oil", "vinegar", "mustard", "sauce", "honey"]):
            return "spices_and_condiments"
        if any(t in text for t in ["kimchi", "frozen"]):
            return "frozen"
        return "produce"

    def _recipe_title(self, cuisine: str, meal: str, main_ingredient: str, index: int) -> str:
        template = self.recipe_title_templates[index % len(self.recipe_title_templates)]
        return template.format(cuisine=cuisine, meal=meal, main=main_ingredient.title())

    def _humanize_seed_data(self, db: Session, min_items: int) -> None:
        """Upgrade old generic seed labels/titles to human-friendly content."""
        realistic_names = self._build_realistic_ingredient_names(max(min_items, db.query(Ingredient).count()))
        ingredients = db.query(Ingredient).order_by(Ingredient.id.asc()).all()
        rename_map: Dict[str, str] = {}
        for idx, ingredient in enumerate(ingredients):
            if idx >= len(realistic_names):
                break
            if ingredient.label.startswith("ingredient ") or "blend" in ingredient.label:
                new_label = realistic_names[idx]
                ingredient.label = new_label
                ingredient.category = self._infer_category(new_label)
                rename_map[ingredient.external_id] = new_label
            else:
                rename_map[ingredient.external_id] = ingredient.label

        recipes = db.query(Recipe).order_by(Recipe.id.asc()).all()
        for idx, recipe in enumerate(recipes):
            ingredient_list = recipe.ingredients or []
            for item in ingredient_list:
                ing_id = item.get("id")
                if ing_id in rename_map:
                    item["name"] = rename_map[ing_id]
            recipe.ingredients = ingredient_list
            if "Bowl" in recipe.title or recipe.title.lower().startswith(("italian", "korean", "mexican", "american")):
                main = ingredient_list[0]["name"] if ingredient_list else "seasonal ingredients"
                recipe.title = self._recipe_title(recipe.cuisine, recipe.meal, main, idx)
                recipe.summary = f"A {recipe.meal} recipe inspired by {recipe.cuisine} cuisine with {main} and balanced macros."
                embedding_text = f"{recipe.title} {recipe.summary} {recipe.cuisine} {recipe.meal} {' '.join([ri.get('name','') for ri in ingredient_list])}"
                recipe.embedding = self.create_embedding(embedding_text)
        db.commit()

    def create_embedding(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dimensions
            sign = -1.0 if int(digest[8:10], 16) % 2 else 1.0
            vector[idx] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        return sum(i * j for i, j in zip(a, b))

    def ensure_seed_data(self, db: Session, min_items: int = 500) -> None:
        ingredient_count = db.query(Ingredient).count()
        recipe_count = db.query(Recipe).count()
        if ingredient_count >= min_items and recipe_count >= min_items:
            self._humanize_seed_data(db, min_items)
            return

        randomizer = random.Random(self.seed_value)
        ingredient_names = self._build_realistic_ingredient_names(min_items)

        if ingredient_count < min_items:
            to_create = min_items - ingredient_count
            for i in range(to_create):
                index = ingredient_count + i + 1
                name = ingredient_names[index - 1]
                unit = "gram" if index % 3 else "ml"
                category = self._infer_category(name)
                calories = 50 + (index % 400)
                protein = round((index % 30) * 0.6, 2)
                carbs = round((index % 50) * 0.8, 2)
                fats = round((index % 20) * 0.4, 2)
                ingredient = Ingredient(
                    external_id=f"ing{index:04d}",
                    label=name,
                    unit=unit,
                    quantity=100.0,
                    nutrition={
                        "calories": float(calories),
                        "protein": float(protein),
                        "carbs": float(carbs),
                        "fats": float(fats),
                        "vitamin_d_mcg": round((index % 8) * 0.3, 2),
                        "vitamin_b12_mcg": round((index % 6) * 0.2, 2),
                        "iron_mg": round((index % 12) * 0.7, 2),
                    },
                    category=category,
                    aliases=[name, name.replace("-", " ").replace("_", " ")],
                )
                db.add(ingredient)
            db.commit()

        ingredients = db.query(Ingredient).order_by(Ingredient.id.asc()).all()

        if recipe_count < min_items:
            to_create = min_items - recipe_count
            for i in range(to_create):
                index = recipe_count + i + 1
                cuisine = self.cuisines[index % len(self.cuisines)]
                meal = self.meal_types[index % len(self.meal_types)]
                selected = randomizer.sample(ingredients, k=6)

                recipe_ingredients = []
                prep = []
                nutrition_totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fats": 0.0}
                for step_idx, ing in enumerate(selected, start=1):
                    qty = float(70 + ((index + step_idx) % 90))
                    recipe_ingredients.append(
                        {"id": ing.external_id, "name": ing.label, "quantity": qty, "unit": ing.unit}
                    )
                    if ing.nutrition:
                        scale = qty / max(float(ing.quantity or 100.0), 1.0)
                        for key in nutrition_totals:
                            nutrition_totals[key] += float(ing.nutrition.get(key, 0.0)) * scale
                    prep.append(
                        {
                            "step": f"Step {step_idx}",
                            "description": f"Prepare {ing.label} and combine into the dish.",
                            "ingredients": [ing.external_id],
                        }
                    )

                tag_one = self.dietary_tags[index % len(self.dietary_tags)]
                tag_two = self.dietary_tags[(index + 5) % len(self.dietary_tags)]
                main_ing = str(recipe_ingredients[0]["name"]) if recipe_ingredients else "seasonal ingredients"
                title = self._recipe_title(cuisine, meal, main_ing, index)
                summary = f"A {meal} recipe inspired by {cuisine} cuisine featuring {main_ing} and balanced macros."

                embedding_text = f"{title} {summary} {cuisine} {meal} {' '.join([ri['name'] for ri in recipe_ingredients])}"
                recipe = Recipe(
                    external_id=f"r{index:04d}",
                    title=title,
                    cuisine=cuisine,
                    meal=meal,
                    servings=2 + (index % 3),
                    ingredients=recipe_ingredients,
                    summary=summary,
                    time=15 + (index % 45),
                    difficulty_level="easy" if index % 3 else "medium",
                    dietary_tags=[tag_one, tag_two],
                    source="seed-rag-database",
                    img=f"/images/recipe-{index:04d}.jpg",
                    preparation=prep,
                    nutrition={k: round(v, 2) for k, v in nutrition_totals.items()},
                    embedding=self.create_embedding(embedding_text),
                    rating_avg=round(3.5 + (index % 15) * 0.1, 2),
                    rating_count=5 + (index % 100),
                )
                db.add(recipe)
            db.commit()

    def search_recipes(
        self,
        db: Session,
        query: str,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self.ensure_seed_data(db)
        query_embedding = self.create_embedding(query or "")
        filters = filters or {}

        candidates = db.query(Recipe).all()
        results: List[Dict[str, Any]] = []
        for recipe in candidates:
            if filters.get("cuisine") and recipe.cuisine.lower() != str(filters["cuisine"]).lower():
                continue
            if filters.get("meal") and recipe.meal.lower() != str(filters["meal"]).lower():
                continue
            if filters.get("dietary_restrictions"):
                restrictions = {str(x).lower().replace(" ", "_") for x in filters["dietary_restrictions"]}
                tags = {str(x).lower().replace(" ", "_") for x in (recipe.dietary_tags or [])}
                if not restrictions.issubset(tags):
                    continue
            if filters.get("max_prep_time") and recipe.time > int(filters["max_prep_time"]):
                continue
            if filters.get("max_calories") and recipe.nutrition:
                if float(recipe.nutrition.get("calories", 0.0)) > float(filters["max_calories"]):
                    continue

            score = self.cosine_similarity(query_embedding, recipe.embedding or [])
            if recipe.rating_avg:
                # Community-driven weighting: prioritize highly-rated recipes.
                score += min(float(recipe.rating_avg) / 10.0, 0.5)
            results.append(
                {
                    "id": recipe.external_id,
                    "title": recipe.title,
                    "relevance_score": round(score, 4),
                    "recipe": recipe,
                }
            )

        results.sort(key=lambda item: item["relevance_score"], reverse=True)
        return results[:top_k]

    def build_augmented_prompt(self, user_query: str, retrieved: List[Dict[str, Any]]) -> str:
        context_lines: List[str] = []
        for item in retrieved:
            recipe: Recipe = item["recipe"]
            context_lines.append(
                f"- {recipe.title} | cuisine={recipe.cuisine} | meal={recipe.meal} | "
                f"tags={recipe.dietary_tags} | nutrition={recipe.nutrition}"
            )
        joined_context = "\n".join(context_lines)
        return (
            f"User request: {user_query}\n"
            f"Retrieved recipe context:\n{joined_context}\n"
            "Use this context to produce a realistic, preference-aligned recipe response."
        )


rag_service = RAGService()
