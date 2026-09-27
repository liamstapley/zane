# ZANE

Local, offline-first agent workflow scaffold for HenHacks sponsorship and
CS+Social Good operations. A routing-only orchestrator selects exactly one
isolated domain runtime. Mock data needs no Google account or API key.

## Quick start (Windows PowerShell)

```powershell
python -m venv backend\.venv
& backend\.venv\Scripts\python.exe -m pip install -e 'backend[test]'
Copy-Item .env.example .env
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend proxies `/api` to port 8000.
The default database is `backend/zane.db`. JSON fixtures are immutable demo
seeds; approved changes are stored in SQLite and persist across restarts.
The `.env` file is optional for the offline path; never commit real keys.

## Verification

```powershell
& backend\.venv\Scripts\python.exe -m pytest backend\tests
Set-Location frontend
npm run build
```

See [architecture](docs/architecture.md) and [development notes](docs/development.md).
