from typing import Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    # We may later add context like history, but for 5A it's stateless.

class ToolResult(BaseModel):
    tool_name: str
    result: Any

class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    timing: dict | None = None
