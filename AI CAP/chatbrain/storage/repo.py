from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Optional

try:
    from sqlmodel import Field, Session, SQLModel, create_engine
except ImportError:  # pragma: no cover
    Field = Session = SQLModel = create_engine = None  # type: ignore


if SQLModel is not None:
    class InteractionLog(SQLModel, table=True):  # type: ignore
        id: Optional[int] = Field(default=None, primary_key=True)
        session_id: str
        user_message: str
        bot_reply: str
        top_k: str
        chosen: Optional[str]
        score: Optional[float]
        stack_depth: int
else:  # pragma: no cover - fallback
    InteractionLog = object  # type: ignore


class SQLiteRepo:
    def __init__(self, path: Optional[str] = None, enabled: Optional[bool] = None) -> None:
        if enabled is None:
            flag = os.getenv("USE_SQLITE_LOG", "false").lower()
            enabled = flag in {"1", "true", "yes"}
        if path is None:
            path = os.getenv("SQLITE_PATH", "chatbrain_logs.db")
        self.path = path
        self.enabled = enabled and SQLModel is not None
        self._engine = None
        if self.enabled:
            self._init_engine()

    def _init_engine(self) -> None:
        if SQLModel is None:
            return
        if self._engine is None:
            self._engine = create_engine(f"sqlite:///{self.path}")
            SQLModel.metadata.create_all(self._engine)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled and SQLModel is not None
        if self.enabled and self._engine is None:
            self._init_engine()

    @contextmanager
    def session(self) -> Iterable[Session]:  # pragma: no cover - được gọi gián tiếp
        if not self.enabled:
            yield None
            return
        if self._engine is None:
            self._init_engine()
        with Session(self._engine) as sess:
            yield sess

    def log_interaction(
        self,
        session_id: str,
        message: str,
        reply: str,
        top_k: list[Dict[str, Any]],
        chosen: Optional[Dict[str, Any]],
        stack_depth: int,
    ) -> None:
        if not self.enabled or SQLModel is None:
            return
        record = InteractionLog(
            session_id=session_id,
            user_message=message,
            bot_reply=reply,
            top_k=json.dumps(top_k, ensure_ascii=False),
            chosen=json.dumps(chosen, ensure_ascii=False) if chosen else None,
            score=chosen.get("score") if chosen else None,
            stack_depth=stack_depth,
        )
        with self.session() as sess:
            if sess is None:
                return
            sess.add(record)
            sess.commit()
