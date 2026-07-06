# Repository Guidelines

## Project Structure & Module Organization

This repository contains a browser-based Magies games platform split into a Python backend and Vue frontend. Backend code lives in `backend/app/`: FastAPI routes in `main.py`, WebSocket handling in `ws.py`, and Dou Dizhu game logic in `game/`. Backend tests are in `backend/tests/`. Frontend code lives in `frontend/src/`, with views in `views/`, Pinia stores in `stores/`, Three.js scenes in `three/`, global styles in `styles/`, and static PWA assets in `frontend/public/`. Utility scripts live in `tools/`; planning docs live in `docs/`.

## Build, Test, and Development Commands

- `cd backend && python -m venv .venv && source .venv/bin/activate`: create and enter a local Python environment.
- `cd backend && pip install -r requirements.txt pytest`: install backend dependencies and pytest.
- `cd backend && python -m uvicorn app.main:app --reload`: run the API and WebSocket server on port 8000.
- `cd backend && python -m pytest`: run backend tests.
- `cd frontend && npm install`: install frontend dependencies from `package-lock.json`.
- `cd frontend && npm run dev`: start Vite on port 5173 with backend proxies.
- `cd frontend && npm run build`: produce the production frontend bundle.

## Coding Style & Naming Conventions

Use small, focused changes and match local style. Python uses 4-space indentation, type hints where helpful, `snake_case` functions, and pytest-style `test_*` names. Keep game rules pure under `backend/app/game/`; API and WebSocket layers should validate, route, and serialize. Frontend JavaScript uses ES modules, single quotes, no semicolons, 2-space indentation, PascalCase Vue views/components, and lower-camel module names such as `api.js`.

## Testing Guidelines

Write or update tests before changing behavior. Put backend tests in `backend/tests/test_*.py` and shared helpers in `backend/tests/conftest.py`. Cover rule-engine edge cases, invalid actions, turn order, settlement, AI behavior, and WebSocket paths. Maintain at least 80% coverage for touched logic. There is no frontend test harness yet; for UI changes, run `npm run build` and manually verify the affected flow.

## Commit & Pull Request Guidelines

Follow the existing Conventional Commit pattern, for example `feat(backend): add room state machine` or `fix(frontend): reconnect websocket`. Keep PRs small and scoped. Include a summary, linked issue when applicable, commands run, and screenshots or recordings for visible UI changes.

## Security & Configuration Tips

Do not commit local secrets, `.env*`, database files, or generated data under `backend/data/`; these are ignored by `.gitignore`. Keep rewards virtual-only: no cash deposits, withdrawals, exchanges, rake, referral payouts, or equivalent mechanics.
