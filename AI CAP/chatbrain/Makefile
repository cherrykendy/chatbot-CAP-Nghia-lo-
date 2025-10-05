.PHONY: install dev test run

install:
python3 -m venv .venv && . .venv/bin/activate && pip install -r chatbrain/requirements.txt

dev:
UVICORN_RELOAD=1 USE_EMBEDDING=false USE_SQLITE_LOG=false uvicorn chatbrain.app:app --reload

test:
USE_EMBEDDING=false USE_SQLITE_LOG=false pytest chatbrain/tests -q

run:
uvicorn chatbrain.app:app --reload
