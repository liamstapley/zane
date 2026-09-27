# Development and local demo

Use Python 3.12+ (3.12 target). Create a project-local environment:

```powershell
python -m venv backend\.venv
& backend\.venv\Scripts\python.exe -m pip install -e 'backend[test]'
& backend\.venv\Scripts\python.exe -m pytest backend\tests
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

On macOS/Linux replace the interpreter invocation with
`backend/.venv/bin/python`. In `frontend`, run `npm ci`, `npm run dev` and
`npm run build`. The Vite dev server proxies `/api` to `localhost:8000`.

Model-free demo requires no `.env`; copy `.env.example` for a custom database
or optional Ollama/OpenAI provider. For Ollama, run it independently and set
`ZANE_MODEL_PROVIDER=ollama`, `ZANE_OLLAMA_BASE_URL`, and
`ZANE_OLLAMA_MODEL` to a model already installed locally. ZANE does not start
the service or pull models. If starting outside the repo root, set an
absolute `ZANE_DATABASE_PATH`.

API highlights: `POST /api/tasks` with `{"message":"..."}`;
`GET /api/tasks/{id}`; `POST /api/tasks/{id}/clarify` with
`{"answer":"Northstar Labs"}`; `POST /api/tasks/{id}/decision` with
`{"approved":true}`; `GET /api/artifacts`,
`GET /api/artifacts/{id}`, `GET /api/artifacts/{id}/export`;
`GET /api/capabilities`; `POST /api/demo/reset` with
`{"confirmation":"RESET DEMO DATA"}`. Reset irreversibly clears the local
demo database before reseeding, not source fixtures.
