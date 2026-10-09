# Investment Portfolio

## Local development

### Backend

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload
```

The API is available at http://localhost:8000.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The Vite dev server proxies `/api/*` to the FastAPI backend.

## Validation

```bash
cd backend && uv run pytest
cd backend && uv run ruff check .
cd frontend && pnpm typecheck
cd frontend && pnpm lint
```

## Portfolio engine documentation

Per una guida operativa sullo schema dati e sul motore di calcolo EUR:

- [`backend/PORTFOLIO_ENGINE.md`](backend/PORTFOLIO_ENGINE.md)
