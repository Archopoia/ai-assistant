from __future__ import annotations

import string
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..api import get_current_user
from ..database import get_db
from ..models.assistant_conversation import AssistantConversation
from ..models.assistant_message import AssistantMessage
from ..models.user import User
from ..schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConversationCreate,
    AssistantConversationDetail,
    AssistantConversationSummary,
    AssistantMessageResponse,
)
from ..services.assistant_service import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _contains_unsupported_control_chars(text: str) -> bool:
    for char in text:
        codepoint = ord(char)
        if codepoint < 32 and char not in {"\n", "\r", "\t"}:
            return True
    return False


def _looks_like_symbol_noise(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 4:
        return False
    alnum_count = sum(1 for char in stripped if char.isalnum())
    symbol_count = sum(1 for char in stripped if char in string.punctuation)
    if alnum_count == 0 and symbol_count > 0:
        return True
    return symbol_count > alnum_count * 2 and len(stripped.split()) <= 2


def _to_summary(conversation: AssistantConversation) -> AssistantConversationSummary:
    return AssistantConversationSummary.model_validate(conversation)


def _to_message(message: AssistantMessage) -> AssistantMessageResponse:
    return AssistantMessageResponse.model_validate(message)


@router.post("/conversations", response_model=AssistantConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: AssistantConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = AssistantConversation(
        user_id=current_user.id,
        title=(payload.title or "Wellness Assistant Chat").strip()[:120] or "Wellness Assistant Chat",
        response_mode=payload.response_mode,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return _to_summary(conversation)


@router.get("/conversations", response_model=list[AssistantConversationSummary])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == current_user.id)
        .order_by(AssistantConversation.created_at.desc())
        .all()
    )
    return [_to_summary(item) for item in conversations]


@router.get("/conversations/latest", response_model=AssistantConversationSummary | None)
async def latest_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == current_user.id)
        .order_by(AssistantConversation.created_at.desc())
        .first()
    )
    if not conversation:
        return None
    return _to_summary(conversation)


@router.get("/conversations/{conversation_id}", response_model=AssistantConversationDetail)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.id == conversation_id, AssistantConversation.user_id == current_user.id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.conversation_id == conversation.id)
        .order_by(AssistantMessage.created_at.asc())
        .all()
    )
    return AssistantConversationDetail(conversation=_to_summary(conversation), messages=[_to_message(m) for m in messages])


@router.post("/conversations/{conversation_id}/messages", response_model=AssistantChatResponse)
async def send_message(
    conversation_id: int,
    payload: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.id == conversation_id, AssistantConversation.user_id == current_user.id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    cleaned_message = (payload.message or "").strip()
    if not cleaned_message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message cannot be empty.")
    if len(cleaned_message) > 6000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message exceeds 6000 characters.")
    if _contains_unsupported_control_chars(cleaned_message):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message includes unsupported control characters. Please remove hidden/binary characters and retry.",
        )
    if _looks_like_symbol_noise(cleaned_message):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message appears malformed (mostly symbols). Please send a readable wellness question.",
        )

    if payload.response_mode:
        conversation.response_mode = payload.response_mode
        db.commit()
        db.refresh(conversation)

    user_message = AssistantMessage(conversation_id=conversation.id, role="user", content=cleaned_message)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    assistant_message, chart_payload, suggestion = assistant_service.chat(
        db=db,
        conversation=conversation,
        current_user=current_user,
        user_message=user_message,
    )
    db.refresh(conversation)
    return AssistantChatResponse(
        conversation=_to_summary(conversation),
        user_message=_to_message(user_message),
        assistant_message=_to_message(assistant_message),
        chart=chart_payload,
        suggested_visualization=suggestion,
    )
