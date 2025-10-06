import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("USE_EMBEDDING", "false")
os.environ.setdefault("USE_SQLITE_LOG", "false")

from chatbrain.app import service


def setup_module(_: object) -> None:
    service.load_scripts("chatbrain/examples")


def test_nlu_match() -> None:
    session_id = "nlu"
    service.clear_context(session_id)
    cases = {
        "kích hoạt vneid": "cai_va_kich_hoat_vneid",
        "quên passcode": "quen_mat_khau_vneid",
        "lệ phí định danh tổ chức": "hoi_le_phi",
    }
    for text, expected in cases.items():
        response = service.handle_message(session_id, text)
        chosen = response.debug["chosen"]
        assert chosen is not None
        assert chosen["intent_id"] == expected
        assert chosen["score"] >= service.policy.threshold
        service.clear_context(session_id)
