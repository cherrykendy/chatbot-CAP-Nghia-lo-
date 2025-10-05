from __future__ import annotations

import json
from typing import Optional

from ..app import BUTTON_LABELS, service


def prompt(text: str) -> str:
    try:
        return input(text)
    except EOFError:  # pragma: no cover
        return ""


def reload_scripts() -> None:
    folder = prompt("Đường dẫn thư mục scripts: ") or "knowledge_base/scripts"
    try:
        result = service.load_scripts(folder)
        print(f"Đã nạp {result['intents']} intents từ {folder}.")
    except Exception as exc:  # pragma: no cover - xử lý runtime
        print(f"Lỗi nạp scripts: {exc}")


def list_intents() -> None:
    domain = prompt("Nhập domain (bỏ trống nếu muốn xem tất cả): ") or None
    intents = service.list_intents(domain)
    if not intents:
        print("Chưa có intent nào.")
        return
    for intent in intents:
        print(f"- {intent['id']} (domain={intent['domain']}, version={intent['version']}, interrupt={intent['can_interrupt']})")


def show_context() -> None:
    session_id = prompt("Session ID: ") or "demo"
    state = service.context_state(session_id)
    print(f"Stack depth: {len(state.stack)}")
    for frame in state.stack:
        print(f"  • {frame.intent_id}#{frame.step_id} (v{frame.version}) - nguồn {frame.script_file}")
    if state.pending_resume:
        print(f"Đang chờ quay lại: {state.pending_resume}")


def simulate_chat() -> None:
    session_id = prompt("Session ID (mặc định demo): ") or "demo"
    print("Nhập tin nhắn. Gõ 'exit' để thoát. Lệnh nhanh: /btn \"Đã xong\", /back, /cancel")
    while True:
        text = prompt("Bạn: ")
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break
        normalized = text
        if text.startswith("/btn"):
            normalized = text[4:].strip().strip('"')
        elif text == "/back":
            normalized = "Quay lại"
        elif text == "/cancel":
            normalized = "Huỷ"
        response = service.handle_message(session_id, normalized)
        print(f"Bot: {response.reply}")
        ui = response.ui
        buttons = None
        if ui is not None:
            buttons = getattr(ui, "buttons", None)
            if buttons is None and hasattr(ui, "get"):
                buttons = ui.get("buttons")
        if buttons:
            print("Nút gợi ý:", ", ".join(buttons))
        print("Top-k:", json.dumps(response.debug.get("top_k", []), ensure_ascii=False, indent=2))
        print("Đang chọn:", json.dumps(response.debug.get("chosen"), ensure_ascii=False))
        print("Độ sâu stack:", response.debug.get("stack_depth"))


def toggle_logging() -> None:
    flag = prompt("Bật logging SQLite? (y/n): ").lower() in {"y", "yes", "1"}
    service.set_logging(flag)
    status = "bật" if flag else "tắt"
    print(f"Đã {status} ghi log.")


def main() -> None:
    actions = {
        "1": reload_scripts,
        "2": list_intents,
        "3": show_context,
        "4": simulate_chat,
        "5": toggle_logging,
    }
    while True:
        print("\n==== ChatBrain Menu ====")
        print("[1] Reload scripts")
        print("[2] Xem danh sách intents")
        print("[3] Xem Context Stack")
        print("[4] Mô phỏng hội thoại")
        print("[5] Bật/Tắt logging SQLite")
        print("[0] Thoát")
        choice = prompt("Chọn chức năng: ")
        if choice == "0":
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Lựa chọn không hợp lệ.")


if __name__ == "__main__":  # pragma: no cover - entry CLI
    main()
