# Portfolio Tracker — istruzioni per Copilot

## Scopo
Webapp mono-utente, senza autenticazione, per tracciare portafogli personali composti
principalmente da FONDI DI INVESTIMENTO e CERTIFICATI, identificati per ISIN.
Tutti i valori economici sono calcolati e mostrati in EUR.

## Stack (vincolante)
- frontend/: template Sneat Vuetify Pro, versione TypeScript, già presente nel repo.
  Vue 3 + Vite + Vuetify 3 + Pinia + Vue Router (file-based routing del template).
  Riusa layout, componenti, tema e libreria grafici GIÀ inclusi nel template; non aggiungere
  altre UI library. Rimuovi pagine/demo non usate solo quando una issue lo chiede.
- backend/: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, SQLite.
  Gestione dipendenze con uv (pyproject.toml). Nessun ORM/DB alternativo.
- Il frontend NON chiama mai provider esterni: parla solo con il backend (/api/...).

## Principi
- Modularità: ogni provider dati è un modulo isolato dietro un'interfaccia.
  Nessun codice di dominio importa direttamente un provider concreto.
- Modifiche mirate: tocca solo i file necessari alla issue corrente.
- Denaro: usa Decimal (backend) e mai float per importi, quantità, prezzi, cambi.
  Persisti come stringa/NUMERIC, non REAL.
- Date: solo date di calendario (ISO yyyy-mm-dd), niente timezone sugli storici EOD.
- Segreti solo da variabili d'ambiente; fornisci `.env.example`, mai chiavi nel codice.

## Test
- Backend: pytest. I test NON devono fare chiamate di rete: usa provider fake e fixture JSON
  registrate in backend/tests/fixtures/. L'ambiente dell'agente ha un firewall.
- Frontend: `vue-tsc --noEmit` e lint del template devono passare.
- Ogni PR deve far passare: `uv run pytest`, `uv run ruff check`, typecheck e lint frontend.

## Comandi
- Backend dev: `cd backend && uv run uvicorn app.main:app --reload`
- Migrazioni: `cd backend && uv run alembic upgrade head`
- Frontend dev: `cd frontend && pnpm dev` (proxy Vite verso il backend su /api)

## Aggiorna questo file quando introduci nuove convenzioni o comandi.