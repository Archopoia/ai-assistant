## Cursor Cloud specific instructions

The runnable product is the conversational assistant (`frontend` route `/assistant`, API prefix `/assistant`). It is not a separate service. It lives in the same FastAPI app and React app as the rest of this repo, and it needs Postgres plus a verified login. Meal plans, recipes, and profiles are tools the assistant calls; you do not need to exercise those pages to develop the chat.

Local dev uses PostgreSQL on the VM, the FastAPI app in `backend/`, and the Vite app in `frontend/`. Docker Compose is the documented full-stack path (`docker-compose.yml`, README). It is not required here: the Compose frontend image is an Nginx production build, and the API is published on host port 8001.

PostgreSQL 16 is installed as cluster `16/main` on port **5432** (database `wellness_db`, user/password `postgres`/`postgres`). systemd often does not start it in this VM. If `pg_isready` fails, run `sudo pg_ctlcluster 16 main start`.

The update script creates `backend/venv` and installs `backend/requirements.txt` plus `frontend` npm deps. Run Alembic and Uvicorn from `backend/` so Pydantic loads `backend/.env` (`env_file = ".env"` is the process cwd, not the repo root). That file is gitignored. Use:

- `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/wellness_db` (the default host `db` only resolves inside Compose)
- `SECRET_KEY` set to any non-empty dev value
- `APP_URL=http://localhost:8000`
- `FRONTEND_URL=http://localhost:3000`
- `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASSWORD` empty

Copying root `.env.example` as-is makes the mailer try Gmail: those SMTP values do not match the placeholder skip list in `backend/app/services/email_service.py`.

```bash
cd backend && ./venv/bin/alembic upgrade head
cd backend && ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev -- --host 0.0.0.0 --port 3000
```

Startup seeds at least 500 ingredients and 500 recipes (`backend/app/services/rag_service.py`). Leave `VITE_API_BASE_URL` unset so the Vite proxy in `frontend/vite.config.ts` forwards `/api` to `http://localhost:8000`. `frontend/.env.example` points at the Compose port 8001.

`POST /auth/login` returns 403 until `users.email_verified` is true, and register does not return the verification token. With SMTP unset, mark the row verified:

```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d wellness_db -c "UPDATE users SET email_verified=true WHERE email='USER@EMAIL';"
```

`npm run lint` in `frontend/` fails: ESLint is a dependency and a script, but there is no ESLint config. `npx tsc --noEmit` in `frontend/` is the typecheck that works. Backend check is `python -m compileall backend/app` (README). There is no automated test suite. Meal plans and the assistant run on local fallbacks when `OPENAI_API_KEY` is empty. Google/GitHub OAuth stay 503 until both client id and secret are set.
