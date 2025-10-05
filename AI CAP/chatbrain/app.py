from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .core import loader
from .core.context import ContextManager
from .core.executor import Executor
from .core.nlu import NLUIndex
from .core.policy import Policy
from .core.schema import Candidate, ContextState, ScriptPack
from .storage.repo import SQLiteRepo

BUTTON_LABELS = {
    "Đã xong",
    "Quay lại",
    "Huỷ",
    "Cần trợ giúp thêm",
    "Không",
    "Tiếp tục",
    "Khởi động lại",
}


class MessageRequest(BaseModel):
    session_id: str
    message: str


class MessageResponse(BaseModel):
    reply: str
    ui: Dict[str, Any]
    debug: Dict[str, Any]


class LoadRequest(BaseModel):
    folder: str


class ChatBrainService:
    def __init__(self) -> None:
        self.context = ContextManager()
        self.nlu = NLUIndex()
        self.policy = Policy()
        self.executor = Executor(self.context)
        self.repo = SQLiteRepo()
        self.script_pack = ScriptPack(intents=[])
        default_folder = os.getenv("CHATBRAIN_DEFAULT_SCRIPTS", "knowledge_base/scripts")
        try:
            self.load_scripts(default_folder)
        except Exception:
            # Cho phép khởi động ngay cả khi chưa có kịch bản
            pass

    # Script management -------------------------------------------------
    def load_scripts(self, folder: str) -> Dict[str, Any]:
        pack = loader.load_from_folder(folder)
        self.script_pack = pack
        self.nlu.build(pack)
        self.executor.load_script_pack(pack)
        return {"intents": len(pack.intents), "folder": folder}

    # Message handling --------------------------------------------------
    def handle_message(self, session_id: str, message: str) -> MessageResponse:
        if not message:
            raise HTTPException(status_code=400, detail="Tin nhắn không hợp lệ")
        normalized = message.strip()
        pending_resume = self.context.pending_resume(session_id)
        if pending_resume and normalized not in {"Quay lại", "Không"}:
            reply = f"Anh/chị đang tạm dừng **{pending_resume}**. Vui lòng chọn 'Quay lại' hoặc 'Không' giúp em nhé."
            response = self._build_response(session_id, reply, {}, [], None)
            self._log(session_id, normalized, response)
            return response
        if session_id in self.executor.version_prompts and normalized not in {"Tiếp tục", "Khởi động lại"}:
            reply = "Nội dung đã cập nhật, anh/chị hãy chọn 'Tiếp tục' hoặc 'Khởi động lại' giúp em nhé."
            response = self._build_response(session_id, reply, {}, [], None)
            self._log(session_id, normalized, response)
            return response

        if normalized in BUTTON_LABELS:
            result = self.executor.handle_button(session_id, normalized)
            response = self._build_response(session_id, result["reply"], result.get("ui", {}), [], None)
            self._log(session_id, normalized, response)
            return response

        top_k = self.nlu.rank(normalized)
        chosen = self.policy.choose(top_k, self.context.peek(session_id))
        if self.policy.is_below_threshold(chosen):
            reply = self.policy.fallback_ask()
            response = self._build_response(session_id, reply, {}, top_k, None)
            self._log(session_id, normalized, response)
            return response

        intent = self.nlu.intent_by_id(chosen.intent_id)
        if intent is None:
            raise HTTPException(status_code=500, detail="Intent không tồn tại")
        interruption = self.policy.should_interrupt(chosen, self.context.peek(session_id))
        result = self.executor.execute_intent(session_id, intent, interruption)
        response = self._build_response(session_id, result["reply"], result.get("ui", {}), top_k, chosen)
        self._log(session_id, normalized, response)
        return response

    # Helpers -----------------------------------------------------------
    def _build_response(
        self,
        session_id: str,
        reply: str,
        ui: Dict[str, Any],
        top_k: List[Candidate],
        chosen: Optional[Candidate],
    ) -> MessageResponse:
        debug_top_k = [c.dict() for c in top_k]
        debug_chosen = chosen.dict() if chosen else None
        stack_depth = len(self.context.stack(session_id))
        response = MessageResponse(
            reply=reply,
            ui=ui,
            debug={
                "top_k": debug_top_k,
                "chosen": debug_chosen,
                "stack_depth": stack_depth,
            },
        )
        return response

    def _log(self, session_id: str, message: str, response: MessageResponse) -> None:
        self.repo.log_interaction(
            session_id=session_id,
            message=message,
            reply=response.reply,
            top_k=response.debug.get("top_k", []),
            chosen=response.debug.get("chosen"),
            stack_depth=response.debug.get("stack_depth", 0),
        )

    # Misc --------------------------------------------------------------
    def list_intents(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        intents = self.nlu.all_intents()
        if domain:
            intents = [i for i in intents if i.domain == domain]
        return [i.dict() for i in intents]

    def context_state(self, session_id: str) -> ContextState:
        return self.context.state(session_id)

    def clear_context(self, session_id: str) -> None:
        self.context.clear(session_id)

    def set_logging(self, enabled: bool) -> None:
        self.repo.set_enabled(enabled)


service = ChatBrainService()
app = FastAPI(title="ChatBrain API")


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/load-scripts")
async def load_scripts(body: LoadRequest) -> Dict[str, Any]:
    result = service.load_scripts(body.folder)
    return {"message": "Đã nạp kịch bản", **result}


@app.get("/intents")
async def list_intents(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    return service.list_intents(domain)


@app.get("/context/{session_id}")
async def get_context(session_id: str) -> ContextState:
    return service.context_state(session_id)


@app.post("/context/{session_id}/clear")
async def clear_context(session_id: str) -> Dict[str, str]:
    service.clear_context(session_id)
    return {"message": "Đã xoá stack"}


@app.post("/message")
async def post_message(body: MessageRequest) -> MessageResponse:
    return service.handle_message(body.session_id, body.message)
