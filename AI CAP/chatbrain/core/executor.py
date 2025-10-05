from __future__ import annotations

from typing import Dict, Optional

from .context import ContextManager
from .schema import ContextFrame, Intent, ScriptPack


class Executor:
    def __init__(self, context: ContextManager) -> None:
        self.context = context
        self.script_pack = ScriptPack(intents=[])
        self.version_prompts: Dict[str, str] = {}

    def load_script_pack(self, pack: ScriptPack) -> None:
        self.script_pack = pack

    # Hook placeholders -------------------------------------------------
    def _run_hook(self, hook_name: Optional[str], session_id: str, intent: Intent, step_id: str) -> None:
        if not hook_name:
            return
        func = getattr(self, hook_name, None)
        if callable(func):
            func(session_id=session_id, intent=intent, step_id=step_id)

    def noop(self, **kwargs) -> None:  # pragma: no cover - ví dụ hook
        return None

    # Core execution ----------------------------------------------------
    def execute_intent(self, session_id: str, intent: Intent, interruption: bool) -> Dict[str, object]:
        frame = self.context.peek(session_id)
        if frame and frame.intent_id == intent.id and not interruption:
            return self._render_current_step(session_id, frame, intent)

        new_frame = ContextFrame(
            script_file=intent.source_file or "unknown",
            intent_id=intent.id,
            domain=intent.domain,
            step_id=intent.steps[0].id,
            step_index=0,
            version=intent.version,
            interruption=interruption,
        )
        self.context.push(session_id, new_frame)
        return self._render_current_step(session_id, new_frame, intent, run_hooks=True)

    def advance_step(self, session_id: str) -> Dict[str, object]:
        frame = self.context.peek(session_id)
        if not frame:
            return self._message("Hiện không có quy trình nào đang chạy.")
        intent = self._intent_by_id(frame.intent_id)
        if not intent:
            self.context.pop(session_id)
            return self._message("Em chưa có thông tin về quy trình trước đó.")
        if self._check_version_prompt(session_id, frame, intent):
            return self._check_version_prompt(session_id, frame, intent)
        if frame.step_index + 1 < len(intent.steps):
            frame.step_index += 1
            frame.step_id = intent.steps[frame.step_index].id
            return self._render_current_step(session_id, frame, intent, run_hooks=True)
        popped = self.context.pop(session_id)
        if popped and popped.interruption:
            previous = self.context.peek(session_id)
            if previous:
                self.context.set_pending_resume(session_id, previous.intent_id)
                return {
                    "reply": f"Anh/chị có muốn quay lại **{previous.intent_id}** không?",
                    "ui": {"buttons": ["Quay lại", "Không"]},
                }
        return self._message("Công việc đã hoàn tất. Anh/chị cần hỗ trợ gì thêm không?")

    def previous_step(self, session_id: str) -> Dict[str, object]:
        frame = self.context.peek(session_id)
        if not frame:
            return self._message("Không có bước nào để quay lại.")
        intent = self._intent_by_id(frame.intent_id)
        if not intent:
            return self._message("Không tìm thấy thông tin quy trình.")
        if frame.step_index == 0:
            return {
                "reply": "Đang ở bước đầu tiên, anh/chị hãy tiếp tục nhé.",
                "ui": self._current_ui(intent, frame),
            }
        frame.step_index -= 1
        frame.step_id = intent.steps[frame.step_index].id
        return self._render_current_step(session_id, frame, intent)

    def clear_task(self, session_id: str) -> Dict[str, object]:
        popped = self.context.pop(session_id)
        if not popped:
            return self._message("Hiện không có quy trình nào để huỷ.")
        if popped.interruption:
            previous = self.context.peek(session_id)
            if previous:
                self.context.set_pending_resume(session_id, previous.intent_id)
                return {
                    "reply": f"Anh/chị có muốn quay lại **{previous.intent_id}** không?",
                    "ui": {"buttons": ["Quay lại", "Không"]},
                }
        return self._message("Em đã huỷ quy trình hiện tại. Anh/chị cần gì thêm cứ nói nhé.")

    def handle_button(self, session_id: str, label: str) -> Dict[str, object]:
        label = label.strip()
        pending = self.context.pending_resume(session_id)
        if pending and label in {"Quay lại", "Không"}:
            if label == "Quay lại":
                self.context.pop_pending_resume(session_id)
                frame = self.context.peek(session_id)
                if not frame:
                    return self._message("Không còn quy trình nào để quay lại.")
                intent = self._intent_by_id(frame.intent_id)
                if not intent:
                    return self._message("Không tìm thấy thông tin quy trình.")
                return self._render_current_step(session_id, frame, intent)
            else:
                self.context.pop_pending_resume(session_id)
                return self._message("Dạ vâng, nếu cần hỗ trợ thêm anh/chị cứ nói nhé.")

        if session_id in self.version_prompts:
            intent_id = self.version_prompts[session_id]
            frame = self.context.peek(session_id)
            intent = self._intent_by_id(intent_id)
            if not frame or not intent:
                self.version_prompts.pop(session_id, None)
                return self._message("Em chưa thể tiếp tục do thiếu dữ liệu.")
            if label == "Tiếp tục":
                frame.version = intent.version
                self.version_prompts.pop(session_id, None)
                return self._render_current_step(session_id, frame, intent)
            if label == "Khởi động lại":
                frame.version = intent.version
                frame.step_index = 0
                frame.step_id = intent.steps[0].id
                self.version_prompts.pop(session_id, None)
                return self._render_current_step(session_id, frame, intent)
            return self._message("Anh/chị vui lòng chọn một trong các nút gợi ý giúp em nhé.")

        if label == "Đã xong":
            return self.advance_step(session_id)
        if label == "Quay lại":
            return self.previous_step(session_id)
        if label == "Huỷ":
            return self.clear_task(session_id)
        if label == "Cần trợ giúp thêm":
            return self._message("Em sẽ kết nối hỗ trợ viên để giúp anh/chị chi tiết hơn nhé.")
        if label == "Không":
            return self._message("Vâng ạ, nếu cần anh/chị cứ nhắn tiếp nhé.")
        return self._message("Em đã ghi nhận." )

    # Helpers -----------------------------------------------------------
    def _intent_by_id(self, intent_id: str) -> Optional[Intent]:
        return self.script_pack.intent_by_id(intent_id)

    def _current_ui(self, intent: Intent, frame: ContextFrame) -> Dict[str, object]:
        step = intent.steps[frame.step_index]
        if step.ui:
            return step.ui.dict()
        return {}

    def _render_current_step(
        self,
        session_id: str,
        frame: ContextFrame,
        intent: Intent,
        run_hooks: bool = False,
    ) -> Dict[str, object]:
        version_message = self._check_version_prompt(session_id, frame, intent)
        if version_message:
            return version_message
        step = intent.steps[frame.step_index]
        self._run_hook(step.before_hook, session_id, intent, step.id)
        self._run_hook(step.action, session_id, intent, step.id)
        self._run_hook(step.after_hook, session_id, intent, step.id)
        ui = step.ui.dict() if step.ui else {}
        return {"reply": step.say, "ui": ui}

    def _check_version_prompt(self, session_id: str, frame: ContextFrame, intent: Intent) -> Optional[Dict[str, object]]:
        if frame.version != intent.version:
            self.version_prompts[session_id] = intent.id
            return {
                "reply": "Nội dung đã cập nhật. Anh/chị muốn tiếp tục hay khởi động lại?",
                "ui": {"buttons": ["Tiếp tục", "Khởi động lại"]},
            }
        return None

    def _message(self, text: str) -> Dict[str, object]:
        return {"reply": text, "ui": {}}
