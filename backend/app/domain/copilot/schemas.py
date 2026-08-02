import datetime
import uuid
from typing import Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)

class ToolResult(BaseModel):
    tool_name: str
    result: Any

class ActionProposalOutput(BaseModel):
    action_id: uuid.UUID
    action_type: str
    status: str
    expires_at: datetime.datetime
    payload: dict[str, Any]
    # For UI display purposes
    display_title: str
    display_subtitle: str
    display_quantity: str

class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    timing: dict | None = None
    action_proposals: list[ActionProposalOutput] = Field(default_factory=list)

class ActionExecuteResponse(BaseModel):
    status: str
    message: str
