from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("assistant_conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("AssistantConversation", back_populates="messages")
