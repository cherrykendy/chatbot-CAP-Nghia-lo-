import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("USE_EMBEDDING", "false")
os.environ.setdefault("USE_SQLITE_LOG", "false")

from chatbrain.app import service


def setup_module(_: object) -> None:
    service.load_scripts("chatbrain/examples")


def test_interrupt_and_resume_flow() -> None:
    session_id = "flow"
    service.clear_context(session_id)

    resp1 = service.handle_message(session_id, "tôi muốn kích hoạt vneid")
    assert "mở ứng dụng VNeID" in resp1.reply
    assert resp1.debug["stack_depth"] == 1

    resp2 = service.handle_message(session_id, "Đã xong")
    assert "Tại màn hình chính" in resp2.reply

    resp3 = service.handle_message(session_id, "tôi quên mật khẩu vneid")
    assert "Quên mật khẩu" in resp3.reply or "quên mật khẩu" in resp3.reply.lower()
    assert resp3.debug["stack_depth"] == 2

    resp4 = service.handle_message(session_id, "Đã xong")
    assert "liên hệ tổng đài" in resp4.reply

    resp5 = service.handle_message(session_id, "Đã xong")
    assert "Anh/chị có muốn quay lại" in resp5.reply
    assert "cai_va_kich_hoat_vneid" in resp5.reply
    assert resp5.ui["buttons"] == ["Quay lại", "Không"]

    state_mid = service.context_state(session_id)
    assert len(state_mid.stack) == 1
    assert state_mid.pending_resume == "cai_va_kich_hoat_vneid"

    resp6 = service.handle_message(session_id, "Quay lại")
    assert "Tại màn hình chính" in resp6.reply
    state_end = service.context_state(session_id)
    assert len(state_end.stack) == 1
    assert state_end.stack[0].step_id == "b2_mo"
