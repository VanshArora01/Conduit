# Conduit

**Connect Everything. Ask Anything.**

Conduit is a production-grade AI Knowledge Operating System that unifies documents, connectors, and conversational retrieval in one workspace.

## Monorepo layout

| Path | Role |
|------|------|
| `backend/` | FastAPI + Planner/Executor AI OS + indexing + RAG |
| `frontend/` | Next.js app (chat, knowledge, developer panel) |
| `docker/` / `docker-compose.yml` | Local infra (e.g. Qdrant) |
| `docs/` | Architecture notes |

## Prerequisites

- Python 3.13+ and [uv](https://github.com/astral-sh/uv)
- Node.js 20+
- PostgreSQL (Neon or local)
- Qdrant (local Docker or cloud)

## Quick start (development)

### 1. Backend

```bash
cd backend
cp .env.example .env   # fill in real secrets locally — never commit .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App: http://localhost:3000

The Next.js app proxies `/api/v1/*` to the backend (see `frontend/next.config.ts`), so same-origin fetches work without CORS issues.

### 3. Optional local Qdrant

```bash
docker compose up -d
```

## Environment & secrets

- Commit **only** `.env.example` files (placeholders).
- Keep real keys in `backend/.env` and `frontend/.env.local` (gitignored).
- Rotate any keys that were ever pasted into example files.

## Production checklist

1. Set `ENVIRONMENT=production` and `DEBUG=False`.
2. Use strong unique `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY`.
3. Point `DATABASE_URL` and `QDRANT_*` at managed services.
4. Configure CORS origins for your real frontend domain.
5. Set frontend `BACKEND_URL` (server rewrite target) and deploy Next + API behind HTTPS.
6. Run migrations: `uv run alembic upgrade head`.
7. Run AI tests before release: `cd backend && uv run pytest tests/ai -q`.

## License

See [LICENSE](./LICENSE).
