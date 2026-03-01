# MetaboDash MVP

MetaboDash is a frontend/backend separated MVP for health assistant detection:
- Health dashboard (glucose + calorie)
- Meal photo upload + meal time confirmation
- Context-aware health chatbot with SSE streaming

## Stack

- `backend/`: FastAPI + SQLAlchemy + Alembic + Celery + Postgres + Redis
- `frontend/`: Vite + React + TypeScript + Tailwind + React Query + Recharts
- `docker-compose`: one-command local startup

## Quick Start

1. Start everything:

```bash
docker compose up --build
```

2. Open:

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

3. Basic flow:

- Register a user in frontend
- Import glucose (`/api/glucose/import`) with CSV/JSON
- Upload meal photo in Meals page
- Confirm meal time + kcal
- Enable AI consent in Settings
- Ask questions in Chat page

## API Modules

- Auth: `/api/auth/*`
- User & consent: `/api/users/*`
- Glucose import/summary: `/api/glucose/*`
- Meal/photo upload flow: `/api/meals/*`
- Dashboard aggregation: `/api/dashboard/*`
- Chat + SSE stream: `/api/chat` and `/api/chat/stream`

## Notes

- Chat endpoint enforces user AI consent (`allow_ai_chat=true`), otherwise returns 403.
- Provider abstraction supports `openai`, `gemini`, and `mock` fallback.
- Current OpenAI/Gemini adapters include TODO fallbacks for structured parsing and official endpoint wiring.

## Tests

Backend unit tests:

```bash
cd backend
pytest -q
```

Frontend e2e smoke:

```bash
cd frontend
npm run e2e
```
