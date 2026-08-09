# 🚚 Prime Crest Logistics Tracking Platform

A logistics and shipment tracking platform: a FastAPI backend and a React
(Vite) frontend with a live-tracking portal, an admin operations dashboard,
and a Leaflet dark-mode route map.

This build covers the **core tracking flow end-to-end** (public lookup +
admin create/update) with **real JWT-based admin authentication** — tested
and working. Remaining Phase 2 items (Supabase migration, PDF waybills,
notifications) are called out at the bottom as next steps.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, Uvicorn
- **Database**: SQLite locally → swap `DATABASE_URL` for Postgres/Supabase in production
- **Frontend**: React 18, Vite 5, Tailwind CSS, Leaflet.js

## Project structure

```
prime-tracking-app/
├── backend/
│   ├── database.py       # DB engine/session (SQLite dev, Postgres via env var)
│   ├── models.py         # Shipment + Milestone + AdminUser ORM models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── auth.py           # bcrypt password hashing + JWT issue/verify
│   ├── main.py           # API routes + CORS + JWT bearer auth guard
│   ├── seed.py           # Seeds two sample shipments for local testing
│   ├── create_admin.py   # Creates/resets an admin login
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api.js                    # fetch client + status color/stage helpers
    │   ├── App.jsx                   # nav switcher: public vs admin
    │   └── components/
    │       ├── TrackingPortal.jsx    # public search box
    │       ├── TrackingDetails.jsx   # status card, Leaflet route map, timeline
    │       └── AdminDashboard.jsx    # sign-in, shipment list, create + milestone forms
    └── .env.example
```

## Quick start

**1. Backend**

```bash
cd backend
python -m pip install fastapi uvicorn sqlalchemy pydantic bcrypt pyjwt python-multipart
python seed.py                              # creates prime_tracking.db with 2 sample shipments
python create_admin.py savage MyStrongPass1 # creates your admin login (pick your own username/password)
python -m uvicorn main:app --reload --port 8000
```

API docs live at http://localhost:8000/docs

**2. Frontend** (new terminal)

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:5173

## Try it

- **Public tracking**: search `PCL085263034594XYZ` or `PCL994810238120ABC`
- **Admin**: switch to the Admin tab, sign in with the username/password you
  set with `create_admin.py`, create a shipment, then add a milestone to
  watch its status and timeline update live. The session token is stored in
  `sessionStorage` and expires after 8 hours (configurable via
  `JWT_EXPIRES_MINUTES`).

## API reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Health check |
| GET | `/api/v1/shipments/track/{tracking_number}` | No | Public tracking lookup |
| POST | `/api/v1/admin/login` | No | Exchange username/password for a JWT |
| GET | `/api/v1/admin/shipments` | Bearer JWT | List all shipments |
| POST | `/api/v1/admin/shipments` | Bearer JWT | Create shipment |
| POST | `/api/v1/admin/shipments/{tracking_number}/milestones` | Bearer JWT | Append a milestone (also updates headline status) |

## What's built and verified

- ✅ SQLAlchemy models with cascade delete on milestones
- ✅ Pydantic validation, including a whitelist of valid status values
- ✅ Public + admin endpoints, smoke-tested end-to-end (create → add milestone → track)
- ✅ Real admin authentication: bcrypt-hashed passwords, JWT issue/verify, 401 on missing/invalid/expired tokens, verified with a wrong-password and a wrong-token case
- ✅ React tracking portal wired to the real API (no mock data)
- ✅ Leaflet dark map with origin/destination/current-location markers and route line
- ✅ Admin dashboard: username/password sign-in, sign-out, shipment list, create-shipment form, add-milestone form
- ✅ Production build verified clean (`npm run build`, no warnings)

## Security notes before deploying anywhere real

- Set `JWT_SECRET` to a long random value (`python -c "import secrets; print(secrets.token_hex(32))"`) — never ship the dev default.
- Change the default admin password created by `create_admin.py` if you used the no-argument default.
- Lock `CORS_ORIGINS` down to your real frontend domain instead of `*`.

## Migrating to Supabase / Postgres

Verified locally against a real Postgres 16 instance — every endpoint (public
tracking, login, admin list, create shipment, add milestone) passed against
Postgres with **zero code changes**, only a `DATABASE_URL` swap.

**1. Create a Supabase project** at supabase.com, then grab your connection
string from Project Settings → Database → Connection string → URI. Use the
**Session pooler** string for a normal long-running backend (Render/Railway);
use the **Transaction pooler** string if deploying somewhere serverless.

**2. Install the Postgres driver:**

```powershell
python -m pip install psycopg2-binary
```

(Or just `python -m pip install -r requirements.txt`, which now includes it.)

**3. Point the backend at Supabase.** Edit `backend\.env` (create it from
`.env.example` if you don't have one yet):

```
DATABASE_URL=postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-xx-xxxx-1.pooler.supabase.com:5432/postgres
```

**4. Recreate your data on the new database** — tables aren't shared between
SQLite and Supabase, so run these once against the new `DATABASE_URL`:

```powershell
python create_admin.py savage MyStrongPass1
python seed.py
```

**5. Start the backend as usual** — `python -m uvicorn main:app --reload --port 8000`.
Everything else (frontend, API routes, JWT auth) works identically; the
database is a drop-in swap.

**Rolling back**: just remove `DATABASE_URL` from `.env` (or set it back to
the SQLite string) to go back to local SQLite.

## Deploying

Config files are already in the repo — `render.yaml` (backend) and
`frontend/vercel.json` (frontend). Locally verified that the backend binds
correctly to a dynamic `$PORT` env var, which is how Render/Railway assign
ports at runtime — same `uvicorn main:app --host 0.0.0.0 --port $PORT`
command Render will run.

**0. Push to GitHub first** — both Render and Vercel deploy from a Git repo, not a local folder.

```powershell
cd C:\Users\savage\Desktop\prime-tracking-app
git init
git add .
git commit -m "Prime Crest Logistics tracking platform"
```

Then create a new repo on github.com and follow its "push an existing repository" instructions (`git remote add origin ...`, `git push -u origin main`).

**1. Deploy the backend on Render**

- Go to render.com → New → Blueprint → connect your GitHub repo. Render will detect `render.yaml` automatically.
- Set the two `sync: false` env vars in the Render dashboard:
  - `DATABASE_URL` — your Supabase connection string
  - `CORS_ORIGINS` — leave as `*` for now; you'll update it after the frontend is deployed
- Deploy. Once live, note the URL Render gives you (e.g. `https://prime-crest-tracking-api.onrender.com`).
- Open a Render shell (or run once locally against the same `DATABASE_URL`) to create your admin user: `python create_admin.py savage MyStrongPass1`

**2. Deploy the frontend on Vercel**

- Go to vercel.com → Add New → Project → import the same GitHub repo, set the root directory to `frontend`.
- Add an environment variable: `VITE_API_URL` = your Render backend URL from step 1.
- Deploy. Vercel gives you a URL like `https://prime-crest-tracking.vercel.app`.

**3. Lock down CORS**

Go back to Render → your backend's environment variables → set `CORS_ORIGINS` to your real Vercel URL (no trailing slash) instead of `*`. Redeploy the backend for the change to take effect.

**4. Sanity check**

Visit your Vercel URL, track a sample shipment on the public side, then sign into Admin with the credentials you created in step 1.

**Railway alternative**: `backend/Procfile` is included if you'd rather use Railway instead of Render — Railway auto-detects Procfiles the same way.

## Roadmap (remaining)
- **Email/WhatsApp webhooks** — auto-notify on milestone updates (hook into `add_milestone` in `main.py`).
- **Refresh tokens / logout-everywhere** — current JWTs are stateless and can't be revoked before they expire; add a token blocklist or short-lived access + refresh token pair if that matters for your use case.
#   p r i m e - t r a c k i n g  
 