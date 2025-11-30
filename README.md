# Later - MVP

## Quick start

1. Create `.env` in `backend/`:

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
TAVILY_API_KEY=tvly-...
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
ENVIRONMENT=dev
```

2. Apply database migrations (Supabase / Postgres):

```
psql $DATABASE_URL -f db/migrations/0001_mvp.sql
```

3. Install and run API:

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

4. Test endpoints:

- `POST http://localhost:8000/v1/ingest` body: `{ "url": "https://example.com" }`
- `POST http://localhost:8000/v1/chat` body: `{ "tool_id": "<uuid>", "question": "What is the pricing?" }`

## Notes
- Specs: see `openspec/changes/add-mvp-foundation/`
- UI: minimal web stub can call the API; a full UI will arrive post-MVP polish.

