from __future__ import annotations

import os
from typing import Dict, List, Optional

from .schema import ContextFrame, ContextState


class ContextManager:
    def __init__(self, max_depth: Optional[int] = None) -> None:
        if max_depth is None:
            max_depth = int(os.getenv("MAX_DEPTH", "2"))
        self.max_depth = max(1, max_depth)
        self._sessions: Dict[str, List[ContextFrame]] = {}
        self._pending_resume: Dict[str, Optional[str]] = {}

    def stack(self, session_id: str) -> List[ContextFrame]:
        return self._sessions.setdefault(session_id, [])

    def push(self, session_id: str, frame: ContextFrame) -> None:
        stack = self.stack(session_id)
        stack.append(frame)
        while len(stack) > self.max_depth:
            stack.pop(0)

    def pop(self, session_id: str) -> Optional[ContextFrame]:
        stack = self.stack(session_id)
        if stack:
            frame = stack.pop()
            if not stack:
                self._pending_resume.pop(session_id, None)
            return frame
        return None

    def peek(self, session_id: str) -> Optional[ContextFrame]:
        stack = self.stack(session_id)
        return stack[-1] if stack else None

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._pending_resume.pop(session_id, None)

    def is_task_active(self, session_id: str) -> bool:
        return bool(self.peek(session_id))

    def set_pending_resume(self, session_id: str, intent_id: str) -> None:
        self._pending_resume[session_id] = intent_id

    def pop_pending_resume(self, session_id: str) -> Optional[str]:
        return self._pending_resume.pop(session_id, None)

    def pending_resume(self, session_id: str) -> Optional[str]:
        return self._pending_resume.get(session_id)

    def state(self, session_id: str) -> ContextState:
        return ContextState(
            session_id=session_id,
            stack=list(self.stack(session_id)),
            pending_resume=self._pending_resume.get(session_id),
        )
