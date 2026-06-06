# V2.1 -> V1 Gap Analysis Dashboard — local dev (LLD §15, Plan E0)
# Backend: FastAPI on :8000   Frontend: Vite on :5173 (proxies /api)

.PHONY: help install install-backend install-frontend backend backend-sample \
        frontend dev dev-mock dev-sample test clean

help:
	@echo "Targets:"
	@echo "  make install            - set up backend venv + frontend deps"
	@echo "  make backend            - run FastAPI using backend/.env (http://localhost:8000)"
	@echo "  make backend-sample     - run FastAPI against the small sample workbooks"
	@echo "  make frontend           - run Vite dev server (http://localhost:5173)"
	@echo "  make dev                - backend (per backend/.env) + frontend together"
	@echo "  make dev-mock           - dev against the ~2000-row mock dataset"
	@echo "  make dev-sample         - dev against the small sample (v1.xlsx / v2.1.xlsx)"
	@echo "  make test               - run backend tests"
	@echo "  make clean              - remove venv, node_modules, caches, snapshot"

# Dataset overrides (env vars take precedence over backend/.env)
MOCK_ENV   = V1_PATH=../mockdata/v1_mock.xlsx V2_PATH=../mockdata/v2.1_mock.xlsx ENABLE_OPTIONAL_GAPS=true
SAMPLE_ENV = V1_PATH=../v1.xlsx V2_PATH=../v2.1.xlsx ENABLE_OPTIONAL_GAPS=true

install: install-backend install-frontend

install-backend:
	cd backend && python3 -m venv .venv && \
		. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

backend-sample:
	cd backend && . .venv/bin/activate && $(SAMPLE_ENV) uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Runs both; backend in background, frontend in foreground. Ctrl-C stops the frontend;
# `make clean` or `pkill -f uvicorn` stops the backend.
dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000 & \
		cd frontend && npm run dev

# Explicit dataset variants (override backend/.env via inline env vars)
dev-mock:
	cd backend && . .venv/bin/activate && $(MOCK_ENV) uvicorn app.main:app --reload --port 8000 & \
		cd frontend && npm run dev

dev-sample:
	cd backend && . .venv/bin/activate && $(SAMPLE_ENV) uvicorn app.main:app --reload --port 8000 & \
		cd frontend && npm run dev

test:
	cd backend && . .venv/bin/activate && pytest -q

clean:
	rm -rf backend/.venv backend/.pytest_cache frontend/node_modules frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f backend/.gapdb.sqlite
