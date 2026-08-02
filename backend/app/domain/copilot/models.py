import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.inventory.models import TenantModel


class CopilotActionProposal(TenantModel):
    __tablename__ = "copilot_action_proposals"

    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)


class CopilotConversationMessage(TenantModel):
    __tablename__ = "copilot_conversation_messages"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, tool
    content: Mapped[str] = mapped_column(String, nullable=True)    # The text or JSON string
    tool_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True) # If it's a tool call/response
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
