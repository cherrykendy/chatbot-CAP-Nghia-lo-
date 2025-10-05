from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from .schema import Intent, ScriptPack


class ScriptLoaderError(Exception):
    """Ngoại lệ khi đọc kịch bản."""


def load_from_folder(folder: str) -> ScriptPack:
    path = Path(folder)
    if not path.exists():
        raise ScriptLoaderError(f"Không tìm thấy thư mục: {folder}")

    intents: List[Intent] = []
    for file in sorted(path.glob("*.yaml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        entries = data.get("intents", [])
        if not isinstance(entries, list):
            raise ScriptLoaderError(f"File {file} không đúng định dạng intents")
        for raw_intent in entries:
            intent = Intent(**{**raw_intent, "source_file": file.name})
            if any(existing.id == intent.id for existing in intents):
                raise ScriptLoaderError(f"Intent trùng id: {intent.id}")
            intents.append(intent)

    if not intents:
        raise ScriptLoaderError("Không có intent nào được nạp")

    return ScriptPack(intents=intents)
