from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class InboundModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ContextRequest(InboundModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class TickRequest(InboundModel):
    now: Optional[str] = None
    available_triggers: List[str] = Field(default_factory=list)


class ReplyRequest(InboundModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str
    message: str
    received_at: Optional[str] = None
    turn_number: int


class ContextAcceptedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: Literal[True]
    ack_id: str
    stored_at: str


class TickAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: str
    trigger_id: str
    template_name: str
    template_params: List[Any]
    body: str
    cta: str
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actions: List[TickAction]


class ReplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    uptime_seconds: int
    contexts_loaded: Dict[str, int]


class MetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_name: str
    team_members: List[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str
