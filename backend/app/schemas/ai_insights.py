from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class AIInsightsBase(BaseModel):
    insight_type: str
    content: Dict[str, Any]
    version: Optional[str] = None
    context_snapshot: Optional[Dict[str, Any]] = None


class AIInsightsCreate(AIInsightsBase):
    pass


class AIInsightsResponse(AIInsightsBase):
    id: int
    user_id: int
    generated_at: datetime
    
    class Config:
        from_attributes = True
