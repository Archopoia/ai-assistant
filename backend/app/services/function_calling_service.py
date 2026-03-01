from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError
from sqlalchemy.orm import Session
from ..config import settings
from .nutrition_functions import (
    NutritionFunctionError,
    NutritionTimeoutError,
    NutritionValidationError,
    nutrition_functions,
)


class FunctionCallingService:
    def __init__(self) -> None:
        self.client: Optional[OpenAI] = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculate_nutrition",
                    "description": "Calculates nutritional information for ingredient list and servings.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ingredients": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "quantity": {"type": "number"},
                                        "unit": {"type": "string"},
                                    },
                                    "required": ["name", "quantity"],
                                },
                            },
                            "servings": {"type": "number"},
                        },
                        "required": ["ingredients", "servings"],
                    },
                },
            }
        ]

    def execute_function(self, db: Session, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if function_name != "calculate_nutrition":
            raise NutritionValidationError(f"Unsupported function: {function_name}")
        ingredients = arguments.get("ingredients")
        servings = arguments.get("servings")
        return nutrition_functions.calculate_nutrition(db=db, ingredients=ingredients, servings=servings)

    def safe_execute(self, db: Session, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return {"ok": True, "result": self.execute_function(db, function_name, arguments)}
        except NutritionValidationError as exc:
            return {"ok": False, "error_type": "invalid_values", "message": str(exc)}
        except NutritionTimeoutError as exc:
            return {"ok": False, "error_type": "timeout", "message": str(exc)}
        except NutritionFunctionError as exc:
            return {"ok": False, "error_type": "execution_error", "message": str(exc)}
        except Exception as exc:
            return {"ok": False, "error_type": "execution_error", "message": f"Unexpected function error: {exc}"}

    def run_nutrition_tool_call(
        self, db: Session, ingredients: List[Dict[str, Any]], servings: float, user_prompt: str
    ) -> Dict[str, Any]:
        """
        Calls the model with a nutrition function tool when possible.
        Falls back to direct function execution for reliability.
        """
        if not self.client:
            return self.safe_execute(
                db=db, function_name="calculate_nutrition", arguments={"ingredients": ingredients, "servings": servings}
            )

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_RECIPE_MODEL,
                messages=[
                    {"role": "system", "content": "You must call calculate_nutrition to compute nutrition."},
                    {
                        "role": "user",
                        "content": f"{user_prompt}\nIngredients: {json.dumps(ingredients)}\nServings: {servings}",
                    },
                ],
                tools=self.get_tools(),
                tool_choice={"type": "function", "function": {"name": "calculate_nutrition"}},
                temperature=0.1,
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []
            if not tool_calls:
                return {
                    "ok": False,
                    "error_type": "parsing_error",
                    "message": "Model did not return a function call; using fallback execution.",
                }

            first_call = tool_calls[0]
            args = first_call.function.arguments
            parsed = json.loads(args) if isinstance(args, str) else args
            return self.safe_execute(db=db, function_name=first_call.function.name, arguments=parsed)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error_type": "parsing_error", "message": f"Malformed function arguments: {exc}"}
        except RateLimitError:
            return {"ok": False, "error_type": "rate_limit", "message": "AI rate limit reached. Please retry shortly."}
        except APIConnectionError:
            return {"ok": False, "error_type": "connectivity", "message": "Unable to reach AI service right now."}
        except APIError as exc:
            return {"ok": False, "error_type": "execution_error", "message": f"AI API error: {exc}"}
        except Exception as exc:
            return {"ok": False, "error_type": "execution_error", "message": f"Unexpected tool-call failure: {exc}"}


function_calling_service = FunctionCallingService()
