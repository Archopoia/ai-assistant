from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Wellness Assistant Chat")
    response_mode = Column(String, nullable=False, default="concise")
    topic_hint = Column(String, nullable=True)
    compressed_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="assistant_conversations")
    messages = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at.asc()",
    )
