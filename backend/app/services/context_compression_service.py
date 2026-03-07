from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence


TOPIC_KEYWORDS = {
    "health": {"bmi", "weight", "wellness", "goal", "activity", "fitness", "progress"},
    "nutrition": {"protein", "calories", "carbs", "fats", "macro", "nutrition", "intake"},
    "meal_plan": {"meal", "breakfast", "lunch", "dinner", "plan", "tomorrow", "today", "week"},
    "recipe": {"recipe", "prepare", "ingredients", "cook", "steps"},
    "chart": {"chart", "trend", "graph", "visual", "breakdown", "compare"},
    "safety": {"pain", "chest", "diagnose", "medical", "doctor", "emergency"},
}


@dataclass
class CompressionResult:
    summary: Optional[str]
    topic_hint: Optional[str]
    selected_message_ids: List[int]


class ContextCompressionService:
    def __init__(self, hard_message_limit: int = 18, compression_turn_threshold: int = 10) -> None:
        self.hard_message_limit = hard_message_limit
        self.compression_turn_threshold = compression_turn_threshold

    def detect_topic(self, text: str) -> Optional[str]:
        lowered = (text or "").lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return topic
        return None

    def compress(
        self,
        messages: Sequence[object],
        current_query: str,
        existing_summary: Optional[str],
    ) -> CompressionResult:
        topic = self.detect_topic(current_query)
        if not messages:
            return CompressionResult(summary=existing_summary, topic_hint=topic, selected_message_ids=[])

        # Keep the most recent messages by default.
        recent = list(messages)[-self.hard_message_limit :]
        selected = {getattr(item, "id", 0) for item in recent}

        # Dynamic relevance: include older messages that mention the current topic.
        if topic:
            topic_terms = TOPIC_KEYWORDS.get(topic, set())
            for item in messages:
                if getattr(item, "id", 0) in selected:
                    continue
                content = str(getattr(item, "content", "")).lower()
                if any(term in content for term in topic_terms):
                    selected.add(getattr(item, "id", 0))

        selected_ids = sorted(selected)

        # Only summarize when message history is long enough.
        user_turns = sum(1 for item in messages if getattr(item, "role", "") == "user")
        if user_turns < self.compression_turn_threshold:
            return CompressionResult(summary=existing_summary, topic_hint=topic, selected_message_ids=selected_ids)

        summary = self._build_summary(messages=messages, topic=topic, previous_summary=existing_summary)
        return CompressionResult(summary=summary, topic_hint=topic, selected_message_ids=selected_ids)

    def _build_summary(
        self,
        messages: Iterable[object],
        topic: Optional[str],
        previous_summary: Optional[str],
    ) -> str:
        user_points: List[str] = []
        assistant_points: List[str] = []
        for item in messages:
            role = getattr(item, "role", "")
            text = " ".join(str(getattr(item, "content", "")).strip().split())
            if not text:
                continue
            text = text[:180]
            if role == "user":
                user_points.append(text)
            elif role == "assistant":
                assistant_points.append(text)

        user_points = user_points[-6:]
        assistant_points = assistant_points[-6:]

        summary_lines: List[str] = []
        if previous_summary:
            summary_lines.append(f"Previous summary: {previous_summary}")
        if topic:
            summary_lines.append(f"Current topic focus: {topic}.")
        if user_points:
            summary_lines.append("User discussed: " + "; ".join(user_points))
        if assistant_points:
            summary_lines.append("Assistant covered: " + "; ".join(assistant_points))

        return " ".join(summary_lines)[:1500]


context_compression_service = ContextCompressionService()
