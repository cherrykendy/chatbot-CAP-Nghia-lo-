from __future__ import annotations

import os
from typing import List, Optional

from .schema import Candidate, ContextFrame


class Policy:
    def __init__(self, threshold: Optional[float] = None) -> None:
        if threshold is None:
            threshold = float(os.getenv("CONF_THRESHOLD", "0.55"))
        self.threshold = threshold
        self.system_intents = {"user_confirms_step"}

    def choose(self, candidates: List[Candidate], active: Optional[ContextFrame]) -> Optional[Candidate]:
        if not candidates:
            return None
        best_score = candidates[0].score
        tied = [c for c in candidates if abs(c.score - best_score) < 1e-6]
        if len(tied) > 1 and active is not None:
            same_domain = [c for c in tied if c.domain == active.domain]
            if same_domain:
                tied = same_domain
        if len(tied) > 1:
            interruptives = [c for c in tied if c.can_interrupt]
            if interruptives:
                tied = interruptives
        return tied[0]

    def is_below_threshold(self, candidate: Optional[Candidate]) -> bool:
        if candidate is None:
            return True
        return candidate.score < self.threshold

    def should_interrupt(self, candidate: Candidate, active: Optional[ContextFrame]) -> bool:
        if active is None:
            return False
        if candidate.intent_id in self.system_intents:
            return False
        return candidate.can_interrupt and candidate.intent_id != active.intent_id

    def fallback_ask(self) -> str:
        return "Em chưa hiểu ý anh/chị. Anh/chị có thể mô tả rõ hơn không?"
