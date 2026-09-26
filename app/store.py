from __future__ import annotations

from copy import deepcopy
from threading import RLock
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple


class StateStore:
    """Single-process state with copy-on-write writes and immutable snapshots."""
    SCOPES = ("category", "merchant", "customer", "trigger")

    def __init__(self) -> None:
        self._lock = RLock()
        self.contexts: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.suppressions: Set[str] = set()
        self.merchant_active_conv: Dict[str, str] = {}
        self.opted_out_merchants: Set[str] = set()
        self._scope_index: Dict[str, Set[str]] = {s: set() for s in self.SCOPES}

    def reset(self) -> None:
        with self._lock:
            self.contexts.clear()
            self.conversations.clear()
            self.suppressions.clear()
            self.merchant_active_conv.clear()
            self.opted_out_merchants.clear()
            self._scope_index = {s: set() for s in self.SCOPES}

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        entry = self.contexts.get((scope, context_id))
        return entry["payload"] if entry else None

    def get_context_snapshot(self, scope: str, context_id: str) -> Optional[Mapping[str, Any]]:
        entry = self.contexts.get((scope, context_id))
        if not entry:
            return None
        return MappingProxyType(deepcopy(entry["payload"]))

    def get_version(self, scope: str, context_id: str) -> Optional[int]:
        entry = self.contexts.get((scope, context_id))
        return entry["version"] if entry else None

    def put_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> bool:
        with self._lock:
            cur = self.contexts.get((scope, context_id))
            if cur and cur["version"] >= version:
                return False
            self.contexts[(scope, context_id)] = {"version": version, "payload": deepcopy(payload)}
            self._scope_index.setdefault(scope, set()).add(context_id)
            return True

    def snapshot(self) -> Mapping[Tuple[str, str], Mapping[str, Any]]:
        with self._lock:
            snap = {
                key: MappingProxyType({"version": value["version"], "payload": deepcopy(value["payload"])})
                for key, value in self.contexts.items()
            }
            return MappingProxyType(snap)

    def get_scope_ids(self, scope: str) -> Tuple[str, ...]:
        return tuple(sorted(self._scope_index.get(scope, set())))

    def get_counts(self) -> Dict[str, int]:
        return {scope: len(ids) for scope, ids in self._scope_index.items()}


state = StateStore()
