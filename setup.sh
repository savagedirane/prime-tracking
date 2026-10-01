#!/usr/bin/env bash
# ============================================================================
# Prime Crest Logistics — one-command local setup (macOS / Linux / Git Bash)
#
#   bash setup.sh
#
# Safe to re-run: installs only what's missing, never overwrites an existing
# .env or resets an existing admin password.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Prime Crest Logistics — local setup"

# --- 0. Preflight -----------------------------------------------------------
command -v python3 >/dev/null || { echo "ERROR: python3 not found (need 3.10+) — install from python.org"; exit 1; }
command -v npm >/dev/null || echo "WARNING: npm not found — frontend will be skipped (install Node 18+)"

# --- 1. Backend -------------------------------------------------------------
echo "==> [1/5] Backend: creating virtual environment (backend/.venv)"
cd backend
[ -x .venv/bin/python ] || python3 -m venv .venv
PY=.venv/bin/python

echo "==> [2/5] Backend: installing dependencies"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt

echo "==> [3/5] Backend: creating .env (if missing)"
if [ ! -f .env ]; then
  SECRET=$("$PY" -c "import secrets; print(secrets.token_hex(32))")
  cat > .env <<EOF
# Prime Crest Logistics — backend environment (created by setup.sh)
# Real environment variables always win over this file (e.g. on Render).

# Local database: a SQLite file, created and seeded automatically.
# To use Supabase later, comment this out and paste your project URI:
# DATABASE_URL=postgresql://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-xx-xxxx-1.pooler.supabase.com:5432/postgres
DATABASE_URL=sqlite:///./prime_tracking.db

# JWT signing secret (fresh random value generated at setup)
JWT_SECRET=${SECRET}
JWT_EXPIRES_MINUTES=480

# Allowed frontend origins (comma-separated)
CORS_ORIGINS=http://localhost:5173

# Optional (Phase 2 features)
# NOTIFY_WEBHOOK_URL=            # webhook for shipment/milestone events
# GEOCODE_ENABLED=true           # set false for air-gapped installs
# GEOCODER_USER_AGENT=prime-crest-tracking/1.0 (you@example.com)
# SSE_HEARTBEAT_SECONDS=15
EOF
  echo "        created backend/.env with a fresh JWT secret"
else
  echo "        .env already exists — leaving it untouched"
fi

echo "==> [4/5] Backend: database schema + admin + demo data"
"$PY" -m alembic upgrade head
ADMIN_COUNT=$("$PY" -c "from database import SessionLocal; import models; db=SessionLocal(); print(db.query(models.AdminUser).count()); db.close()")
if [ "$ADMIN_COUNT" = "0" ]; then
  "$PY" create_admin.py admin changeme123
  echo "        NOTE: default login created (admin / changeme123) — change it:"
  echo "              python create_admin.py <yourname> <a-strong-password>"
else
  echo "        admin user(s) already exist ($ADMIN_COUNT) — nothing changed"
fi
"$PY" seed.py

cd ..

# --- 2. Frontend ------------------------------------------------------------
if command -v npm >/dev/null; then
  echo "==> [5/5] Frontend: installing dependencies"
  cd frontend
  npm install --no-fund --no-audit
  cd ..
else
  echo "==> [5/5] Frontend: SKIPPED (npm not found)"
fi

# --- 3. Done ----------------------------------------------------------------
cat <<'EOF'

============================================================
 Setup complete! To run the app, open TWO terminals:

   Terminal 1 (API):
     cd backend
     .venv/bin/python -m uvicorn main:app --reload --port 8000

   Terminal 2 (web app):
     cd frontend
     npm run dev

 Then open  http://localhost:5173
   Admin login:  admin / changeme123   (change it — see above)
   Track demo:   PCL085263034594XYZ
============================================================
EOF
