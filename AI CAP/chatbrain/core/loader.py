from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import yaml

from .schema import Intent, MediaItem, ScriptPack, Step, StepUI


class ScriptLoaderError(Exception):
    """Ngoại lệ khi đọc kịch bản."""


def load_from_folder(folder: str) -> ScriptPack:
    path = Path(folder)
    if not path.exists():
        raise ScriptLoaderError(f"Không tìm thấy thư mục: {folder}")
    if not path.is_dir():
        raise ScriptLoaderError(f"Đường dẫn không phải thư mục: {folder}")

    files = sorted([p for p in path.glob("*.yaml") if p.is_file()])
    if not files:
        raise ScriptLoaderError("Không tìm thấy file YAML nào")

    intents: List[Intent] = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - lỗi IO hiếm gặp
            raise ScriptLoaderError(f"Không thể đọc file {file.name}: {exc}") from exc
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            raise ScriptLoaderError(f"YAML lỗi cú pháp trong {file.name}: {exc}") from exc

        entries = data.get("intents", [])
        if not isinstance(entries, list):
            raise ScriptLoaderError(f"File {file.name} không đúng định dạng intents")

        for raw_intent in entries:
            if not isinstance(raw_intent, dict):
                raise ScriptLoaderError(f"Intent trong {file.name} phải là object")
            normalized_steps = _normalize_steps(raw_intent.get("steps"), file.name)
            intent_payload = {**raw_intent, "steps": normalized_steps, "source_file": file.name}
            try:
                intent = Intent(**intent_payload)
            except Exception as exc:  # pragma: no cover - để báo lỗi rõ ràng
                raise ScriptLoaderError(f"Intent {raw_intent.get('id')} trong {file.name} lỗi: {exc}") from exc
            if any(existing.id == intent.id for existing in intents):
                raise ScriptLoaderError(f"Intent trùng id: {intent.id}")
            intents.append(intent)

    if not intents:
        raise ScriptLoaderError("Không có intent nào được nạp")

    return ScriptPack(intents=intents)


def _normalize_steps(raw_steps: object, file_name: str) -> List[Step]:
    if not isinstance(raw_steps, list):
        raise ScriptLoaderError(f"Intent trong {file_name} thiếu danh sách steps")
    normalized: List[Step] = []
    for index, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            raise ScriptLoaderError(
                f"Step thứ {index + 1} trong {file_name} phải là object"
            )
        payload = dict(item)
        payload.setdefault("say", "")
        payload["say"] = str(payload.get("say", ""))
        payload["ui"] = _normalize_ui(payload.get("ui"), file_name, payload.get("id", f"step_{index}"))
        try:
            step = Step(**payload)
        except Exception as exc:
            raise ScriptLoaderError(
                f"Step {payload.get('id')} trong {file_name} không hợp lệ: {exc}"
            ) from exc
        normalized.append(step)
    return normalized


def _normalize_ui(raw_ui: object, file_name: str, step_id: object) -> StepUI:
    if raw_ui is None:
        return StepUI()
    if not isinstance(raw_ui, dict):
        raise ScriptLoaderError(
            f"UI của step {step_id} trong {file_name} phải là object"
        )

    buttons_raw = raw_ui.get("buttons", [])
    buttons: List[str] = []
    if isinstance(buttons_raw, list):
        for btn in buttons_raw:
            if isinstance(btn, str):
                buttons.append(btn)
            else:
                buttons.append(str(btn))
    elif buttons_raw is None:
        buttons = []
    else:
        buttons = [str(buttons_raw)]

    media_items = _normalize_media(raw_ui.get("media", []), file_name, step_id)
    return StepUI(buttons=buttons, media=media_items)


def _normalize_media(raw_media: object, file_name: str, step_id: object) -> List[MediaItem]:
    if raw_media is None:
        return []
    if not isinstance(raw_media, Iterable) or isinstance(raw_media, (str, bytes)):
        raise ScriptLoaderError(
            f"UI.media của step {step_id} trong {file_name} phải là danh sách"
        )

    items: List[MediaItem] = []
    for idx, entry in enumerate(raw_media):
        if not isinstance(entry, dict):
            raise ScriptLoaderError(
                f"Media item thứ {idx + 1} của step {step_id} trong {file_name} phải là object"
            )
        media_payload = dict(entry)
        media_type = media_payload.get("type", "image") or "image"
        url = media_payload.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ScriptLoaderError(
                f"Media item thứ {idx + 1} của step {step_id} trong {file_name} thiếu url"
            )
        alt = media_payload.get("alt")
        if alt is not None and not isinstance(alt, str):
            alt = str(alt)
        items.append(MediaItem(type=str(media_type), url=url.strip(), alt=alt))
    return items
