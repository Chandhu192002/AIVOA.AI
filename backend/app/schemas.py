"""Pydantic schemas shared by the API routers."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's chat message")
    history: list[ChatHistoryItem] = Field(default_factory=list)
    form_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Current values of the Log Interaction form (snake_case keys)",
    )
    interaction_id: Optional[int] = Field(
        default=None, description="Id of the interaction currently loaded in the form"
    )


class ChatResponse(BaseModel):
    reply: str
    form_updates: dict[str, Any] = Field(default_factory=dict)
    suggested_followups: list[str] = Field(default_factory=list)
    interaction_id: Optional[int] = None
    tool_calls: list[str] = Field(default_factory=list)
    model_used: str = ""


class HCPOut(BaseModel):
    id: int
    name: str
    specialty: str
    institution: str

    class Config:
        from_attributes = True
