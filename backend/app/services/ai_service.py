import json
from typing import Dict, Any, Optional
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError
from ..config import settings
from ..models.ai_insights import AIInsights
from sqlalchemy.orm import Session


class AIService:
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _build_health_status_prompt(self, ai_data: Dict[str, Any]) -> str:
        """Build prompt for health status analysis."""
        return f"""You are a health and wellness advisor. Analyze the following user health data and provide a comprehensive health status analysis.

User Health Data:
{json.dumps(ai_data, indent=2)}

Please provide:
1. Overall health status assessment
2. Key strengths and areas for improvement
3. Risk factors (if any)
4. General recommendations

Format your response as JSON with the following structure:
{{
    "overall_status": "excellent|good|fair|needs_attention",
    "summary": "Brief summary of current health status",
    "strengths": ["strength1", "strength2"],
    "improvements": ["area1", "area2"],
    "risk_factors": ["risk1", "risk2"],
    "recommendations": ["recommendation1", "recommendation2"]
}}"""

    def _build_progress_prompt(self, ai_data: Dict[str, Any]) -> str:
        """Build prompt for progress evaluation."""
        return f"""You are a health and wellness advisor. Evaluate the user's progress based on their health data.

User Health Data:
{json.dumps(ai_data, indent=2)}

Please provide:
1. Progress evaluation compared to goals
2. Notable achievements
3. Areas where progress could be improved
4. Motivational feedback

Format your response as JSON with the following structure:
{{
    "progress_status": "excellent|good|moderate|needs_improvement",
    "summary": "Brief progress summary",
    "achievements": ["achievement1", "achievement2"],
    "improvement_areas": ["area1", "area2"],
    "motivational_message": "Encouraging message",
    "next_steps": ["step1", "step2"]
}}"""

    def _build_recommendations_prompt(self, ai_data: Dict[str, Any]) -> str:
        """Build prompt for personalized recommendations."""
        return f"""You are a health and wellness advisor. Generate personalized recommendations based on the user's health profile, goals, and preferences.

User Health Data:
{json.dumps(ai_data, indent=2)}

Please provide personalized recommendations considering:
- User's current state and goals
- Dietary preferences and restrictions
- Activity level and preferences
- Progress history

Format your response as JSON with the following structure:
{{
    "recommendations": [
        {{
            "category": "nutrition|exercise|lifestyle|habits",
            "title": "Recommendation title",
            "description": "Detailed description",
            "priority": "high|medium|low",
            "actionable_steps": ["step1", "step2"]
        }}
    ],
    "weekly_focus": "Main focus area for the week"
}}"""

    def _build_weekly_summary_prompt(self, ai_data: Dict[str, Any]) -> str:
        """Build prompt for weekly health summary."""
        return f"""You are a health and wellness advisor. Create a weekly health summary for the user.

User Health Data:
{json.dumps(ai_data, indent=2)}

Please provide:
1. Weekly highlights
2. Progress summary
3. Key insights
4. Upcoming week focus

Format your response as JSON with the following structure:
{{
    "week_summary": "Overall week summary",
    "highlights": ["highlight1", "highlight2"],
    "progress_summary": "Progress overview",
    "key_insights": ["insight1", "insight2"],
    "next_week_focus": "Focus area for next week"
}}"""

    def generate_insight(
        self,
        insight_type: str,
        ai_data: Dict[str, Any],
        db: Session,
        user_id: int
    ) -> Optional[AIInsights]:
        """Generate AI insight and store it."""
        if not self.client:
            import logging
            logging.warning("OpenAI client not initialized - API key missing")
            return None
        
        # Select prompt based on insight type
        prompt_builders = {
            "health_status": self._build_health_status_prompt,
            "progress_evaluation": self._build_progress_prompt,
            "recommendations": self._build_recommendations_prompt,
            "weekly_summary": self._build_weekly_summary_prompt
        }
        
        builder = prompt_builders.get(insight_type)
        if not builder:
            return None
        
        try:
            prompt = builder(ai_data)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful health and wellness advisor. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content_text = response.choices[0].message.content
            
            # Try to parse JSON from response
            try:
                # Extract JSON if wrapped in markdown code blocks
                if "```json" in content_text:
                    content_text = content_text.split("```json")[1].split("```")[0].strip()
                elif "```" in content_text:
                    content_text = content_text.split("```")[1].split("```")[0].strip()
                
                content_json = json.loads(content_text)
            except json.JSONDecodeError:
                # Fallback: wrap in a simple structure
                content_json = {"raw_response": content_text}

            content_json = self._validate_against_restrictions(content_json, ai_data)
            
            # Create insight record
            insight = AIInsights(
                user_id=user_id,
                insight_type=insight_type,
                content=content_json,
                version="1.0",
                context_snapshot=ai_data
            )
            
            db.add(insight)
            db.commit()
            db.refresh(insight)
            
            return insight
            
        except RateLimitError as e:
            # Rate limit or quota exceeded
            import logging
            error_msg = str(e)
            logging.error(f"OpenAI rate limit/quota error: {e}")
            # Check if it's a quota issue
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                raise ValueError("OpenAI API quota exceeded. Please check your billing and plan at https://platform.openai.com/account/billing")
            raise ValueError("OpenAI API rate limit exceeded. Please try again later.")
        except APIConnectionError as e:
            # Network error
            import logging
            logging.error(f"OpenAI connection error: {e}")
            raise ValueError("Unable to connect to OpenAI API. Please check your internet connection and try again.")
        except APIError as e:
            # Other API errors
            import logging
            error_msg = str(e)
            logging.error(f"OpenAI API error: {e}")
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                raise ValueError("OpenAI API quota exceeded. Please check your billing and plan at https://platform.openai.com/account/billing")
            raise ValueError(f"OpenAI API error: {error_msg}")
        except Exception as e:
            # Any other error: return None
            import logging
            logging.error(f"Unexpected error generating AI insight: {e}", exc_info=True)
            return None

    def _validate_against_restrictions(self, content_json: Dict[str, Any], ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter recommendations that conflict with dietary restrictions."""
        restrictions = [
            str(r).lower() for r in ai_data.get("user_metrics", {}).get("restrictions", [])
        ]
        recommendations = content_json.get("recommendations")
        if not restrictions or not isinstance(recommendations, list):
            return content_json

        restricted_keywords = {
            "dairy_free": ["dairy", "milk", "cheese", "yogurt", "whey"],
            "gluten_free": ["gluten", "wheat", "barley", "rye"],
            "nut_free": ["nut", "almond", "peanut", "cashew", "walnut"],
            "soy_free": ["soy", "tofu", "edamame"],
            "egg_free": ["egg", "omelet"],
            "shellfish_free": ["shellfish", "shrimp", "crab", "lobster"],
        }

        filtered = []
        for rec in recommendations:
            if isinstance(rec, dict):
                rec_text = f"{rec.get('title', '')} {rec.get('description', '')}".lower()
            else:
                rec_text = str(rec).lower()
            is_conflicting = False
            for restriction in restrictions:
                for keyword in restricted_keywords.get(restriction, []):
                    if keyword in rec_text:
                        is_conflicting = True
                        break
                if is_conflicting:
                    break
            if not is_conflicting:
                filtered.append(rec)

        if filtered:
            content_json["recommendations"] = filtered
        return content_json


ai_service = AIService()
