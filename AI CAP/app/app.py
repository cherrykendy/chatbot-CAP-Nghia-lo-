# app/app.py
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import yaml, os, glob, json

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KB_ROOT  = os.path.join(APP_ROOT, "knowledge_base")
CFG_PATH = os.path.join(APP_ROOT, "config", "app.yaml")
REG_PATH = os.path.join(APP_ROOT, "registry.yaml")

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_config():
    return load_yaml(CFG_PATH)

def load_registry():
    reg = load_yaml(REG_PATH)
    # resolve module paths to abs
    for m in reg.get("modules", []):
        m["abs_path"] = os.path.join(APP_ROOT, m["path"])
    return reg

def load_intents(registry):
    intents = {}
    for m in registry.get("modules", []):
        doc = load_yaml(m["abs_path"])
        # hỗ trợ cả kiểu file 1-intent và nhiều intents
        if "intents" in doc:
            for it in doc["intents"]:
                intents[it["id"]] = it
        else:
            intents[doc["id"]] = doc
    return intents

app = FastAPI(title="AI CAP Bot")

# mount static /assets -> knowledge_base/assets
cfg = load_config()
app.mount(
    cfg["static"]["url_prefix"],
    StaticFiles(directory=os.path.join(APP_ROOT, cfg["static"]["fs_path"])),
    name="assets",
)

STATE = {
    "registry": load_registry(),
}
STATE["intents"] = load_intents(STATE["registry"])

@app.get("/admin/reload")
def reload():
    STATE["registry"] = load_registry()
    STATE["intents"]  = load_intents(STATE["registry"])
    return {"ok": True, "intents": list(STATE["intents"].keys())}

@app.get("/intents")
def list_intents():
    return {"intents": list(STATE["intents"].keys())}

@app.post("/chat")
def chat(message: str = Body(..., embed=True)):
    # ROUTING rất đơn giản (placeholder): khớp theo synonyms/entry_patterns
    text = message.lower().strip()
    for it in STATE["intents"].values():
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
    fb = load_registry().get("fallback", {}).get("answer", "Xin lỗi, tôi chưa có thông tin.")
    return {"matched_intent": None, "answer": fb}

@app.get("/")
def root():
    return {"status": "ok", "intents": list(STATE["intents"].keys())}