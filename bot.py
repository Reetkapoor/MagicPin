"""Compatibility entrypoint; implementation now lives under app/."""
from app.api import app
from app.composer import (
    compose, handle_reply, sanitize_body, get_category_for_merchant,
    format_salutation, format_customer_salutation,
)
from app.schemas import ContextRequest, TickRequest, ReplyRequest
from app.store import StateStore, state

__all__ = [
    "app", "state", "StateStore", "ContextRequest", "TickRequest", "ReplyRequest",
    "compose", "handle_reply", "sanitize_body", "get_category_for_merchant",
    "format_salutation", "format_customer_salutation",
]
