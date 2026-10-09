# AstroScope developer shortcuts. Requires Python 3.11+ and Node 18+.

# Pick the first interpreter on PATH that is Python 3.11+ (override with `make setup PY=python3.12`).
PY ?= $(shell for p in python3.13 python3.12 python3.11 python3 python; do \
	if command -v $$p >/dev/null 2>&1 && $$p -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then echo $$p; break; fi; done)
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help setup setup-backend setup-frontend backend frontend dev test test-backend test-frontend lint build

help:
	@echo "make setup        install backend (.venv) and frontend (node_modules) dependencies"
	@echo "make backend      run the FastAPI server on :8000 (auto-reload)"
	@echo "make frontend     run the Vite dev server on :5173 (proxies /api to :8000)"
	@echo "make test         run backend (pytest) and frontend (vitest) tests"
	@echo "make lint         ruff + tsc"
	@echo "make build        production frontend build into frontend/dist"

setup: setup-backend setup-frontend

setup-backend:
	@if [ -z "$(PY)" ]; then \
		echo "No Python 3.11+ interpreter found on PATH. Install one (e.g. conda create -n astroscope python=3.12) and run: make setup PY=<python>"; exit 1; fi
	@echo "Using $(PY) ($$($(PY) --version))"
	@if [ -x "$(BIN)/python" ] && ! $(BIN)/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then \
		echo "$(VENV) was created with an old Python; removing it"; rm -rf $(VENV); fi
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e "backend[dev]"

setup-frontend:
	cd frontend && npm install

backend:
	cd backend && ../$(BIN)/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && ../$(BIN)/pytest -q

test-frontend:
	cd frontend && npx vitest run

lint:
	cd backend && ../$(BIN)/ruff check app tests && ../$(BIN)/ruff format --check app tests
	cd frontend && npx tsc -b

build:
	cd frontend && npm run build
