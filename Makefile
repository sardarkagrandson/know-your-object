# AstroScope developer shortcuts. Requires Python 3.11+ and Node 18+.

PY ?= python3
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
