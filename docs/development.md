# Local development

Use Python 3.12 or later (3.12 is the production target). Create the isolated
virtual environment at `backend/.venv`; do not install project dependencies
into the system interpreter:

```powershell
python -m venv backend\.venv
& backend\.venv\Scripts\python.exe -m pip install -e 'backend[test]'
& backend\.venv\Scripts\python.exe -m pytest backend\tests
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

For UI development run `npm install` and `npm run dev` from `frontend`.
Run `npm run build` there for TypeScript and production-build validation.

Set `ZANE_MODEL_PROVIDER=openai` and `OPENAI_API_KEY` in a local `.env` only
to classify ambiguous domains via LangChain. The offline default returns an
explicit clarification when neither (or both) domains can be selected.
If starting the server outside the repository root, set an absolute
`ZANE_DATABASE_PATH`. No Google integration or send capability exists.

Test with `POST /api/tasks` (`{"message":"Summarize HenHacks sponsorship status"}`),
inspect `GET /api/tasks/{id}`, and use `POST /api/tasks/{id}/decision`
(`{"approved":true}` or `{"approved":false}`) for a pending mutation.
