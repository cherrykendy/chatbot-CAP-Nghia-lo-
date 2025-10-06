from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class MediaItem(BaseModel):
    type: str = "image"
    url: str
    alt: Optional[str] = None


class StepUI(BaseModel):
    buttons: List[str] = Field(default_factory=list)
    media: List[MediaItem] = Field(default_factory=list)


class Step(BaseModel):
    id: str
    say: str
    ui: StepUI = Field(default_factory=StepUI)
    before_hook: Optional[str] = None
    action: Optional[str] = None
    after_hook: Optional[str] = None

    @field_validator("say", mode="before")
    @classmethod
    def _ensure_say_str(cls, value: object) -> str:
        if value is None:
            raise ValueError("Trường 'say' bắt buộc")
        return str(value)


class Intent(BaseModel):
    id: str
    domain: str
    version: int
    can_interrupt: bool = False
    synonyms: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    required_slots: List[str] = Field(default_factory=list)
    steps: List[Step]
    source_file: Optional[str] = None

    @model_validator(mode="after")
    def _validate_steps(self) -> "Intent":
        if not self.steps:
            raise ValueError("Intent phải có ít nhất một bước")
        ids = set()
        for step in self.steps:
            if step.id in ids:
                raise ValueError(f"Trùng id bước: {step.id}")
            ids.add(step.id)
        return self


class ScriptPack(BaseModel):
    intents: List[Intent]

    def intent_by_id(self, intent_id: str) -> Optional[Intent]:
        return next((i for i in self.intents if i.id == intent_id), None)

    def intents_by_domain(self, domain: str) -> List[Intent]:
        return [i for i in self.intents if i.domain == domain]


class Candidate(BaseModel):
    intent_id: str
    file: Optional[str]
    score: float
    can_interrupt: bool
    domain: str


class ContextFrame(BaseModel):
    script_file: str
    intent_id: str
    domain: str
    step_id: str
    step_index: int
    slots: Dict[str, str] = Field(default_factory=dict)
    version: int
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    interruption: bool = False


class ContextState(BaseModel):
    session_id: str
    stack: List[ContextFrame]
    pending_resume: Optional[str] = None
