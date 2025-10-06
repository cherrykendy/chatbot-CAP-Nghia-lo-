from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import yaml
from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG_PATH = os.path.join(APP_ROOT, "config", "app.yaml")
REG_PATH = os.path.join(APP_ROOT, "registry.yaml")


def load_yaml(path: str, *, label: str) -> Dict[str, Any]:
    """Đọc file YAML với xử lý lỗi an toàn."""

    try:
        with open(path, "r", encoding="utf-8") as stream:
            return yaml.safe_load(stream) or {}
    except FileNotFoundError:
        print(f"LOI: Khong tim thay file {label} tai {path}")
    except yaml.YAMLError as exc:
        print(f"LOI: File {label} sai cu phap: {exc}")
    except OSError as exc:
        print(f"LOI: Khong the doc file {label}: {exc}")
    return {}


def load_config() -> Dict[str, Any]:
    return load_yaml(CFG_PATH, label="config/app.yaml")


def load_registry() -> Dict[str, Any]:
    registry = load_yaml(REG_PATH, label="registry.yaml")
    modules = registry.get("modules", [])
    if isinstance(modules, list):
        for module in modules:
            path = module.get("path")
            if isinstance(path, str):
                module["abs_path"] = os.path.join(APP_ROOT, path)
    return registry


def load_intents(registry: Dict[str, Any]) -> Dict[str, Any]:
    intents: Dict[str, Any] = {}
    modules = registry.get("modules", [])
    if not isinstance(modules, list):
        return intents
    for module in modules:
        abs_path = module.get("abs_path")
        label = module.get("path") or "module"
        if not isinstance(abs_path, str):
            continue
        doc = load_yaml(abs_path, label=label)
        if not doc:
            continue
        module_intents = doc.get("intents")
        if isinstance(module_intents, list):
            for intent in module_intents:
                if isinstance(intent, dict) and "id" in intent:
                    intents[intent["id"]] = intent
        elif isinstance(doc, dict) and "id" in doc:
            intents[doc["id"]] = doc
    return intents


STATE: Dict[str, Dict[str, Any]] = {
    "config": {},
    "registry": {},
    "intents": {},
}


def _mount_static(app: FastAPI, config: Dict[str, Any]) -> None:
    static_cfg = config.get("static", {})
    if not isinstance(static_cfg, dict):
        return
    prefix = static_cfg.get("url_prefix")
    fs_path = static_cfg.get("fs_path")
    if not (isinstance(prefix, str) and isinstance(fs_path, str)):
        return
    directory = os.path.join(APP_ROOT, fs_path)
    already_mounted = any(getattr(route, "path", None) == prefix for route in app.routes)
    if already_mounted:
        return
    try:
        app.mount(prefix, StaticFiles(directory=directory), name="assets")
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        print(f"LOI: Khong the mount static tai {directory}: {exc}")


def _initialize_state(app: FastAPI) -> None:
    STATE["config"] = load_config()
    if STATE["config"]:
        _mount_static(app, STATE["config"])
    STATE["registry"] = load_registry()
    STATE["intents"] = load_intents(STATE["registry"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_state(app)
    yield


app = FastAPI(title="AI CAP Bot", lifespan=lifespan)


@app.get("/admin/reload")
def reload():
    _initialize_state(app)
    return {"ok": True, "intents": list(STATE["intents"].keys())}

@app.get("/intents")
def list_intents():
    return {"intents": list(STATE["intents"].keys())}

@app.post("/chat")
def chat(message: str = Body(..., embed=True)):
    # ROUTING rất đơn giản (placeholder): khớp theo synonyms/entry_patterns
    text = message.lower().strip()
    for it in STATE.get("intents", {}).values():
        # kiểu intent 1 file
        syns = it.get("synonyms", [])
        if any(s.lower() in text for s in syns):
            return JSONResponse({"matched_intent": it["id"], "mode": "final_or_flow", "data": it})
        # kiểu bundle nhiều intents
        for flow in it.get("guided_flows", []) if "guided_flows" in it else []:
            eps = flow.get("entry_patterns", [])
            if any(e.lower() in text for e in eps):
                return JSONResponse({"matched_intent": it["id"], "flow": flow["id"], "step": flow["steps"][0], "data": it})

    # fallback
    registry = STATE.get("registry", {})
    fb = registry.get("fallback", {}).get("answer", "Xin lỗi, tôi chưa có thông tin.")
    return {"matched_intent": None, "answer": fb}

@app.get("/")
def root():
    return {"status": "ok", "intents": list(STATE.get("intents", {}).keys())}
