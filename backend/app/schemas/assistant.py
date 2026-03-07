from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


ResponseMode = Literal["concise", "detailed"]
ChartType = Literal["line", "bar", "pie"]


class ChartPayload(BaseModel):
    chart_type: ChartType
    title: str
    description: str = ""
    x_key: Optional[str] = None
    y_keys: List[str] = Field(default_factory=list)
    data: List[Dict[str, Any]] = Field(default_factory=list)


class AssistantMessageResponse(BaseModel):
    id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AssistantConversationSummary(BaseModel):
    id: int
    title: str
    response_mode: ResponseMode
    topic_hint: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssistantConversationDetail(BaseModel):
    conversation: AssistantConversationSummary
    messages: List[AssistantMessageResponse]


class AssistantConversationCreate(BaseModel):
    title: Optional[str] = Field(default="Wellness Assistant Chat", max_length=120)
    response_mode: ResponseMode = "concise"


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    response_mode: Optional[ResponseMode] = None


class AssistantChatResponse(BaseModel):
    conversation: AssistantConversationSummary
    user_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse
    chart: Optional[ChartPayload] = None
    suggested_visualization: Optional[str] = None
