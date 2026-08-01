# Bharat Business Copilot

Sprint 1 foundation for the Bharat Business Copilot web application.

## Prerequisites

- Node.js 20+
- Python 3.12+
- Docker Desktop (for PostgreSQL)
- A Clerk application (for authenticated routes)

## Quick start

1. Copy `frontend/.env.example` to `frontend/.env.local` and add Clerk keys.
2. Copy `backend/.env.example` to `backend/.env` and set trusted Clerk issuer/audience values.
3. Start the local database: `docker compose up -d db`.
4. Install and run the frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
5. Install and run the backend in another terminal:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   uvicorn app.main:app --reload --port 8000
   ```

The frontend runs at `http://localhost:3000`; FastAPI docs are at `http://localhost:8000/docs`.

## Clerk setup for Sprint 2

1. In Clerk Dashboard, enable **Organizations**.
2. Create roles named `owner`, `admin`, `manager`, `inventory`, and `viewer` (or map your existing `org:*` roles).
3. Create a JWT template named `bharat-api`; set its audience to `bharat-business-copilot` and include the active organization ID (`org_id`) and organization role (`org_role`) claims.
4. Copy **Issuer URL** from Clerk Dashboard → Configure → API Keys to `backend/.env` as `CLERK_ISSUER_URL`.
5. Copy the configured audience to `CLERK_AUDIENCE=bharat-business-copilot` in `backend/.env`.
6. Copy the publishable and secret keys to `frontend/.env.local` as `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`.

## Verification

- Frontend: `npm run lint`, `npm run typecheck`, `npm test`
- Backend: `ruff check .`, `ruff format --check .`, `pytest`

Business modules are intentionally placeholders. Sprint 2 begins only after review.
