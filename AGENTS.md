# Repository Guidelines

## Project Structure & Module Organization

MagiesGames is a browser-based 3D card and board game platform. Backend code lives in `backend/app/`: `main.py` is the FastAPI entrypoint, `ws.py` handles WebSockets, `rooms.py` coordinates rooms, and `auth.py`/`db.py` cover accounts and persistence. Keep pure rule engines under `backend/app/game/`: Dou Dizhu in the root game package, Gomoku in `game/gomoku/`, Sichuan Xue Zhan Mahjong in `game/mahjong/`, and Xiangqi in `game/xiangqi/`. Rule engines must stay independent from networking and storage.

Backend tests live in `backend/tests/test_*.py`, with integration coverage split by game where possible. Frontend code lives in `frontend/src/`, with views in `views/`, Pinia stores in `stores/`, Three.js scenes in `three/`, shared styles in `styles/`, and clients in `api.js`/`ws.js`. Static assets belong in `frontend/public/`; docs and utilities belong in `docs/` and `tools/`.

## Build, Test, and Development Commands

- `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest`: install backend dependencies.
- `cd backend && .venv/bin/python -m pytest tests/ -q`: run all backend tests.
- `cd backend && .venv/bin/python -m pytest tests/test_xiangqi.py tests/test_xiangqi_integration.py -q`: run Xiangqi-specific tests.
- `cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload`: run the API and WebSocket server locally.
- `cd frontend && npm install`: install Vite/Vue dependencies.
- `cd frontend && npm run dev`: start Vite on port 5173 with `/api` and `/ws` proxies.
- `cd frontend && npm run build`: create the production bundle.

Useful test environment variables: `MAGIES_FAST=1` for short timers and `MAGIES_DATA=<dir>` for an isolated data directory.

## Coding Style & Naming Conventions

Use small, focused changes and match nearby code. Python uses 4-space indentation, `snake_case`, pytest-style `test_*` names, and type hints where useful. Frontend JavaScript uses ES modules, 2-space indentation, single quotes, no semicolons, PascalCase Vue components, and lower-camel module names such as `api.js`.

Keep `rooms.py` responsible for room orchestration, turn timers, AI fill-ins, reconnects, and game-type dispatch. Keep `ws.py` responsible for the WebSocket protocol. Clients should treat server snapshots as the source of truth; events are for animation and incremental UI feedback.

## Testing Guidelines

Use pytest for backend coverage. For behavior changes or bug fixes, add or update a failing test before changing production code. Cover rule-engine edge cases, invalid actions, turn order, settlement, AI behavior, account flows, WebSocket paths, spectator behavior, and Mahjong win logic. Aim for 80% coverage on touched logic. There is no frontend test harness; for UI changes, run `npm run build` and verify the route manually.

## Commit & Pull Request Guidelines

History follows Conventional Commits, for example `feat(mahjong-ui): add 3D table flow`, `feat(auth): add account system`, or `docs: update README`. Use `type(scope): description` when useful. Keep PRs small and include a summary, linked issue, commands run, and screenshots or recordings for visible UI changes.

## Security & Configuration Tips

Do not commit secrets, `.env*`, database files, keys, generated data, `backend/data/`, `node_modules/`, or build output. Use `MAGIES_DATA` for local data. Keep rewards virtual-only: no cash deposits, withdrawals, exchanges, rake, referral payouts, or equivalent mechanics. AI robots must not participate in real reward rankings.
