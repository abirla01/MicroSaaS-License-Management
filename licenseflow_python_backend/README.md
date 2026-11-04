# LicenseFlow — Pure Python Backend

This backend uses **Flask + SQLite + JWT**. It does not use Django.

## Included
- JSON REST endpoints used by the current frontend (`/health/`, `/auth/login/`, `/auth/register/`, `/auth/refresh/`, `/auth/me/`, `/customers/`, `/plans/`, `/subscriptions/`, `/licenses/`, `/verify-license/`, `/transactions/`, `/invoices/`, `/dashboard/`).
- CORS enabled for local frontend development.
- Supports the existing SQLite database exported from the previous project for login and read operations. Existing Django PBKDF2 password hashes are checked directly; passwords are not reset.
- When no database is present, it creates a new Flask-compatible SQLite schema.

## Setup on macOS
From the folder containing `app.py`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

The API starts at `http://127.0.0.1:8000`.

Test:
```bash
curl http://127.0.0.1:8000/health/
```

Expected:
```json
{"message":"LicenseFlow backend is running","status":"ok"}
```

## Existing database
The provided archive included `db.sqlite3`. Keep that file next to `app.py` to retain the current legacy records. The app detects its old schema and reads those tables directly.

The included database has legacy Django tables, so registration is intentionally disabled while using it. This avoids silently mixing the old schema with the new schema. If you want new-user registration in this existing database, migrate the data into the new schema first or keep the legacy database backed up.

## JWT secret
For local development the app uses a default development secret. Before deployment, set `LICENSEFLOW_JWT_SECRET` to a long random secret. Do not expose this local development server to the public internet.
