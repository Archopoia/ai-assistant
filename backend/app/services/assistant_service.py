from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from openai import OpenAI
from openai import APIConnectionError, APIError, RateLimitError
from sqlalchemy.orm import Session
from ..config import settings
from ..models.assistant_conversation import AssistantConversation
from ..models.assistant_message import AssistantMessage
from ..models.user import User
from .assistant_tools import assistant_tools_service
from .context_compression_service import context_compression_service


class AssistantService:
    def __init__(self) -> None:
        self.client: Optional[OpenAI] = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_ANALYSIS_MODEL or "gpt-3.5-turbo"

    def chat(
        self,
        db: Session,
        conversation: AssistantConversation,
        current_user: User,
        user_message: AssistantMessage,
    ) -> Tuple[AssistantMessage, Optional[Dict[str, Any]], Optional[str]]:
        response_mode = conversation.response_mode if conversation.response_mode in {"concise", "detailed"} else "concise"
        medical_warning = self._medical_safety_override(user_message.content)
        if medical_warning:
            return self._save_assistant_message(
                db=db,
                conversation=conversation,
                content=medical_warning,
                metadata_json={"mode": response_mode, "safety": "medical"},
            ), None, None

        pii_warning = self._pii_boundary_override(user_message.content)
        if pii_warning:
            return self._save_assistant_message(
                db=db,
                conversation=conversation,
                content=pii_warning,
                metadata_json={"mode": response_mode, "safety": "pii"},
            ), None, None

        out_of_scope_warning = self._out_of_scope_override(user_message.content)
        if out_of_scope_warning:
            return self._save_assistant_message(
                db=db,
                conversation=conversation,
                content=out_of_scope_warning,
                metadata_json={"mode": response_mode, "safety": "scope"},
            ), None, None

        unexpected_input_warning = self._unexpected_input_override(user_message.content)
        if unexpected_input_warning:
            return self._save_assistant_message(
                db=db,
                conversation=conversation,
                content=unexpected_input_warning,
                metadata_json={"mode": response_mode, "safety": "input_validation"},
            ), None, None

        tool_data, fallback_text = self._deterministic_shortcuts(
            db, conversation, current_user, user_message.content, response_mode
        )
        if tool_data.get("chart_payload"):
            chart = tool_data["chart_payload"]
        else:
            chart = None
        if fallback_text and not self.client:
            assistant_message = self._save_assistant_message(
                db=db,
                conversation=conversation,
                content=self._enforce_response_mode(fallback_text, response_mode),
                metadata_json={"mode": response_mode, "chart_payload": chart},
            )
            return assistant_message, chart, self._suggested_visualization(user_message.content, conversation)

        messages = (
            db.query(AssistantMessage)
            .filter(AssistantMessage.conversation_id == conversation.id)
            .order_by(AssistantMessage.created_at.asc())
            .all()
        )
        compression = context_compression_service.compress(
            messages=messages,
            current_query=user_message.content,
            existing_summary=conversation.compressed_summary,
        )
        conversation.topic_hint = compression.topic_hint
        conversation.compressed_summary = compression.summary
        db.commit()

        llm_messages = self._build_llm_messages(
            conversation=conversation,
            response_mode=response_mode,
            messages=[m for m in messages if m.id in set(compression.selected_message_ids)],
        )

        if not self.client:
            content = fallback_text or self._basic_fallback_response(user_message.content, response_mode)
            content = self._enforce_response_mode(content, response_mode)
            assistant_message = self._save_assistant_message(
                db=db,
                conversation=conversation,
                content=content,
                metadata_json={"mode": response_mode, "chart_payload": chart},
            )
            return assistant_message, chart, self._suggested_visualization(user_message.content, conversation, messages)

        content_text = ""
        chart_payload: Optional[Dict[str, Any]] = chart
        try:
            loop_guard = 0
            while loop_guard < 4:
                loop_guard += 1
                response = self.client.chat.completions.create(
                    model=self.default_model,
                    messages=llm_messages,  # type: ignore[arg-type]
                    tools=assistant_tools_service.get_tools(),  # type: ignore[arg-type]
                    tool_choice="auto",
                    temperature=0.3 if response_mode == "concise" else 0.55,
                    top_p=0.9,
                    max_tokens=900 if response_mode == "concise" else 1400,
                )
                message = response.choices[0].message
                tool_calls = message.tool_calls or []
                if not tool_calls:
                    content_text = message.content or ""
                    break

                llm_messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [tc.model_dump() for tc in tool_calls],
                    }
                )
                for tool_call in tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        fn_args = {}
                    result = assistant_tools_service.execute(
                        db=db,
                        current_user=current_user,
                        function_name=fn_name,
                        arguments=fn_args,
                    )
                    tool_result = result.get("result", {}) if result.get("ok") else {"error": result.get("error")}
                    if not chart_payload and isinstance(tool_result, dict) and tool_result.get("chart_payload"):
                        chart_payload = tool_result.get("chart_payload")
                    llm_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        }
                    )
            if not content_text:
                content_text = fallback_text or self._basic_fallback_response(user_message.content, response_mode)
        except (RateLimitError, APIConnectionError, APIError, ValueError):
            content_text = fallback_text or self._basic_fallback_response(user_message.content, response_mode)
            content_text += "\n\nNote: Live model response was temporarily unavailable, so I used a fallback answer."
        content_text = self._enforce_response_mode(content_text, response_mode)

        assistant_message = self._save_assistant_message(
            db=db,
            conversation=conversation,
            content=content_text,
            metadata_json={"mode": response_mode, "chart_payload": chart_payload},
        )
        return assistant_message, chart_payload, self._suggested_visualization(user_message.content, conversation, messages)

    def _build_llm_messages(
        self,
        conversation: AssistantConversation,
        response_mode: str,
        messages: List[AssistantMessage],
    ) -> List[Dict[str, Any]]:
        system_prompt = self._system_prompt(response_mode=response_mode, name_hint=conversation.title.split(" - ")[0])
        output: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if conversation.compressed_summary:
            output.append(
                {
                    "role": "system",
                    "content": "Conversation summary for context continuity: " + conversation.compressed_summary,
                }
            )
        for item in messages:
            output.append({"role": item.role, "content": item.content})
        return output

    def _system_prompt(self, response_mode: str, name_hint: str) -> str:
        verbosity_rule = (
            "Keep responses short (3-6 bullets max, concise phrasing)."
            if response_mode == "concise"
            else "Provide detailed explanations with sections and concrete numbers."
        )
        return f"""
You are a wellness assistant for a health and nutrition platform.

Capabilities:
- Answer health metrics questions (BMI, weight, wellness score, goals, progress).
- Answer meal plan, recipe, and nutrition intake questions.
- Explain trends and chart insights in plain language.
- Maintain context across follow-up questions and references like "that" and "it".

Required behavior:
- Personalize responses using only the user's first-name style display name.
- Never expose sensitive PII (email, DOB, auth credentials) and never retrieve other users' data.
- If user requests diagnosis or urgent symptoms (e.g. chest pain), do not diagnose. Tell them to seek professional medical help immediately.
- Use metric units only (kg, cm, kcal, g).
- Use structured and scannable output with headings and bullets when useful.
- {verbosity_rule}

Examples:
1) Health metrics question:
User: "What's my current BMI?"
Assistant: "Your **BMI** is X (classification). Compared to your target trend: ... "

2) Progress question:
User: "How has my weight changed this month?"
Assistant: "### Monthly weight trend\\n- Start: ... kg\\n- Current: ... kg\\n- Change: ... kg\\n- Interpretation: ..."

3) Meal plan question:
User: "What's my meal plan for today?"
Assistant: "### Today's plan\\n- Breakfast: ...\\n- Lunch: ...\\n- Dinner: ..."

4) Safety boundary:
User: "I've had chest pain while exercising"
Assistant: "I can't provide a diagnosis. Please seek urgent medical care or emergency services."

You must call tools whenever user asks about concrete personal data.
"""

    def _save_assistant_message(
        self,
        db: Session,
        conversation: AssistantConversation,
        content: str,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> AssistantMessage:
        assistant_message = AssistantMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=content.strip(),
            metadata_json=metadata_json or {},
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return assistant_message

    def _medical_safety_override(self, prompt: str) -> Optional[str]:
        lowered = prompt.lower()
        urgent_terms = ["chest pain", "trouble breathing", "severe pain", "fainting", "blood"]
        if any(term in lowered for term in urgent_terms):
            return (
                "I can't diagnose medical conditions. Because these symptoms can be serious, please seek immediate care "
                "from a qualified medical professional or emergency services."
            )
        return None

    def _pii_boundary_override(self, prompt: str) -> Optional[str]:
        lowered = prompt.lower()
        pii_terms = ["email", "date of birth", "dob", "password", "credentials", "other users", "admin mode", "user id"]
        if any(term in lowered for term in pii_terms):
            return (
                "I can only access your wellness data for this authenticated account, and I cannot share sensitive information "
                "like email, date of birth, credentials, or any other user's data."
            )
        return None

    def _out_of_scope_override(self, prompt: str) -> Optional[str]:
        lowered = prompt.lower()
        out_of_scope_terms = ["write code", "stock price", "politics", "weather", "movie recommendation"]
        if any(term in lowered for term in out_of_scope_terms):
            return (
                "I’m focused on wellness support in this app: health metrics, goals, nutrition, meal plans, recipes, "
                "and chart insights. If you'd like, I can help you analyze your current progress in any of those areas."
            )
        return None

    def _unexpected_input_override(self, prompt: str) -> Optional[str]:
        stripped = prompt.strip()
        if not stripped:
            return None

        # Graceful handling of code-like payloads while preserving chat continuity.
        code_patterns = [
            r"```",
            r"\bimport\s+\w+",
            r"\bdef\s+\w+\s*\(",
            r"\bclass\s+\w+",
            r"\bfunction\s+\w*\s*\(",
            r"\bSELECT\s+.+\bFROM\b",
            r"<script\b",
        ]
        if any(re.search(pattern, stripped, flags=re.IGNORECASE) for pattern in code_patterns):
            return (
                "I can’t execute or debug code in this chat, but I can still help with wellness topics. "
                "Try asking your question in health, nutrition, meal-plan, or progress terms."
            )

        symbol_count = sum(1 for ch in stripped if not ch.isalnum() and not ch.isspace())
        if len(stripped) >= 20 and symbol_count / max(len(stripped), 1) > 0.55:
            return (
                "Your message contains a lot of special characters, so I may misread it. "
                "Please rephrase it as a plain wellness question."
            )
        return None

    def _deterministic_shortcuts(
        self,
        db: Session,
        conversation: AssistantConversation,
        current_user: User,
        prompt: str,
        response_mode: str,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        lowered = prompt.lower()
        chart_intent = (
            "chart" in lowered
            or "show me" in lowered
            or lowered.startswith("show ")
            or "trend" in lowered
            or "breakdown" in lowered
            or "compare" in lowered
        )
        if chart_intent:
            if "weight" in lowered:
                result = assistant_tools_service.execute(
                    db, current_user, "get_chart_data", {"chart_kind": "weight_trend", "period": "monthly"}
                )
                if result.get("ok"):
                    base = "### Weight trend chart\n- Period: last 30 days\n- Unit: kg"
                    return result.get("result", {}), self._mode_specific(base, response_mode)
            if "protein" in lowered:
                result = assistant_tools_service.execute(
                    db, current_user, "get_chart_data", {"chart_kind": "protein_vs_target", "period": "weekly"}
                )
                if result.get("ok"):
                    base = "### Protein vs target chart\n- Period: this week\n- Unit: grams"
                    return result.get("result", {}), self._mode_specific(base, response_mode)
            if "macro" in lowered or "macronutrient" in lowered:
                result = assistant_tools_service.execute(
                    db, current_user, "get_chart_data", {"chart_kind": "macro_breakdown", "period": "today"}
                )
                if result.get("ok"):
                    base = "### Macronutrient breakdown chart\n- Period: today\n- Segments: protein, carbs, fats"
                    return result.get("result", {}), self._mode_specific(base, response_mode)

        meal_related = any(
            token in lowered
            for token in [
                "meal plan",
                "custom meal",
                "breakfast",
                "lunch",
                "dinner",
                "tonight",
                "tomorrow meal",
            ]
        )
        if meal_related:
            timeframe = "today"
            if "tomorrow" in lowered:
                timeframe = "tomorrow"
            elif "week" in lowered:
                timeframe = "week"
            elif "latest" in lowered:
                timeframe = "latest"
            result = assistant_tools_service.execute(db, current_user, "get_meal_plan", {"timeframe": timeframe})
            if result.get("ok"):
                plans = result["result"]["plans"]
                chunks: List[str] = [f"### Meal plan ({timeframe})"]
                for plan in plans:
                    chunks.append(f"- **{plan['target_date']}**")
                    for meal in plan.get("meals", []):
                        chunks.append(f"  - {meal.get('meal_type', 'Meal').title()}: {meal.get('name', 'Unnamed meal')}")
                if "prepare" in lowered or "recipe" in lowered or "how do i" in lowered:
                    meal_name = "dinner" if ("dinner" in lowered or "tonight" in lowered) else "lunch" if "lunch" in lowered else "breakfast"
                    recipe_result = assistant_tools_service.execute(
                        db,
                        current_user,
                        "get_recipe_for_meal",
                        {"meal_name": meal_name, "day_hint": timeframe},
                    )
                    if recipe_result.get("ok"):
                        recipe = recipe_result["result"]
                        chunks.append("")
                        chunks.append(f"### Preparation for {recipe.get('meal_name', meal_name)}")
                        for step in (recipe.get("preparation") or []):
                            chunks.append(f"- {step.get('step', 'Step')}: {step.get('description', '')}")
                return {}, self._mode_specific("\n".join(chunks), response_mode)

        if "bmi" in lowered or "weight" in lowered or "wellness score" in lowered:
            result = assistant_tools_service.execute(db, current_user, "get_health_metrics", {"metric_type": "all"})
            if result.get("ok"):
                current = result["result"]["current"]
                trend = result["result"]["trend"]
                text = (
                    "### Current metrics\n"
                    f"- **Weight:** {current.get('weight_kg')} kg\n"
                    f"- **BMI:** {current.get('bmi')} ({current.get('bmi_classification')})\n"
                    f"- **Wellness score:** {current.get('wellness_score')}\n"
                    f"- **Trend:** {trend.get('trend_direction', 'n/a')}\n"
                )
                return {}, self._mode_specific(text, response_mode)
        return {}, None

    def _basic_fallback_response(self, prompt: str, response_mode: str) -> str:
        if response_mode == "detailed":
            return (
                "I processed your request, but a live AI response is currently unavailable.\n\n"
                "I can still help with your health metrics, goals, nutrition summaries, meal plans, and chart requests. "
                "Try asking a direct question like:\n"
                "- What's my current BMI and wellness score?\n"
                "- What's my meal plan for today?\n"
                "- Show my protein intake vs target chart."
            )
        return "I couldn't generate a live model reply right now. Try a direct data question like BMI, meal plan, or protein target."

    def _mode_specific(self, text: str, response_mode: str) -> str:
        if response_mode == "concise":
            return self._to_concise(text)
        return self._to_detailed(text)

    def _enforce_response_mode(self, text: str, response_mode: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return cleaned
        if response_mode == "concise":
            return self._to_concise(cleaned)
        return self._to_detailed(cleaned)

    def _to_concise(self, text: str) -> str:
        # Keep concise answers noticeably shorter than detailed mode.
        if len(text) <= 320 and text.count("\n") <= 4:
            return text
        condensed = " ".join(text.replace("\n", " ").split())
        parts = [segment.strip() for segment in condensed.split(".") if segment.strip()]
        if not parts:
            return condensed[:320]
        short = ". ".join(parts[:2]).strip()
        if short and not short.endswith("."):
            short += "."
        return short[:340]

    def _to_detailed(self, text: str) -> str:
        # Preserve existing detail. If too short, expand slightly with guidance.
        if len(text) >= 260:
            return text
        if "\n" in text or text.endswith("."):
            return text + "\n\nIf you want, I can break this down with your personal targets and current progress."
        return text + "\n\nIf you want, I can break this down with your personal targets and current progress."

    def _suggested_visualization(
        self,
        prompt: str,
        conversation: Optional[AssistantConversation] = None,
        messages: Optional[Sequence[AssistantMessage]] = None,
    ) -> Optional[str]:
        lowered = prompt.lower()
        if any(token in lowered for token in ["chart", "graph", "visual", "show me"]):
            return None

        recent_context = ""
        if messages:
            tail = list(messages)[-6:]
            recent_context = " ".join((item.content or "").lower() for item in tail)

        topic_hint = (conversation.topic_hint or "").lower() if conversation else ""
        nutrition_context = ("protein" in recent_context or "nutrition" in recent_context or topic_hint == "nutrition")
        health_context = ("weight" in recent_context or "wellness" in recent_context or topic_hint == "health")
        macro_context = ("macro" in recent_context or "carbs" in recent_context or "fats" in recent_context)

        if "protein" in lowered or nutrition_context:
            return "Would you like to see a chart of your protein intake versus your target this week?"
        if "weight" in lowered or health_context:
            return "I can also show your weight trend chart for the last month."
        if "macro" in lowered or "macronutrient" in lowered or macro_context:
            return "Would you like a pie chart of today's macronutrient breakdown?"
        return None


assistant_service = AssistantService()
