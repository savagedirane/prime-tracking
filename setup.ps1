# ============================================================================
# Prime Crest Logistics — one-command local setup (Windows PowerShell)
#
#   Right-click this file -> "Run with PowerShell", or from a terminal:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Safe to re-run: installs only what's missing, never overwrites an existing
# .env or resets an existing admin password.
# ============================================================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Prime Crest Logistics - local setup" -ForegroundColor Cyan

# --- 0. Preflight -----------------------------------------------------------
try { $null = Get-Command python -ErrorAction Stop } catch {
  Write-Host "ERROR: python not found (need 3.10+) - install from python.org" -ForegroundColor Red
  exit 1
}

# --- 1. Backend -------------------------------------------------------------
Write-Host "==> [1/5] Backend: creating virtual environment (backend\.venv)"
Push-Location backend
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = ".\.venv\bin\python" }

Write-Host "==> [2/5] Backend: installing dependencies"
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r requirements.txt

Write-Host "==> [3/5] Backend: creating .env (if missing)"
if (-not (Test-Path ".env")) {
  $secret = & $py -c "import secrets; print(secrets.token_hex(32))"
  $lines = @(
    "# Prime Crest Logistics - backend environment (created by setup.ps1)",
    "# Real environment variables always win over this file (e.g. on Render).",
    "",
    "# Local database: a SQLite file, created and seeded automatically.",
    "# To use Supabase later, comment this out and paste your project URI:",
    "# DATABASE_URL=postgresql://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-xx-xxxx-1.pooler.supabase.com:5432/postgres",
    "DATABASE_URL=sqlite:///./prime_tracking.db",
    "",
    "# JWT signing secret (fresh random value generated at setup)",
    "JWT_SECRET=$secret",
    "JWT_EXPIRES_MINUTES=480",
    "",
    "# Allowed frontend origins (comma-separated)",
    "CORS_ORIGINS=http://localhost:5173",
    "",
    "# Optional (Phase 2 features)",
    "# NOTIFY_WEBHOOK_URL=",
    "# GEOCODE_ENABLED=true",
    "# GEOCODER_USER_AGENT=prime-crest-tracking/1.0 (you@example.com)",
    "# SSE_HEARTBEAT_SECONDS=15"
  )
  $lines | Set-Content -Encoding UTF8 .env
  Write-Host "        created backend\.env with a fresh JWT secret"
} else {
  Write-Host "        .env already exists - leaving it untouched"
}

Write-Host "==> [4/5] Backend: database schema + admin + demo data"
& $py -m alembic upgrade head
$adminCount = & $py -c "from database import SessionLocal; import models; db=SessionLocal(); print(db.query(models.AdminUser).count()); db.close()"
if ("$adminCount".Trim() -eq "0") {
  & $py create_admin.py admin changeme123
  Write-Host "        NOTE: default login created (admin / changeme123) - change it:" -ForegroundColor Yellow
  Write-Host "              python create_admin.py <yourname> <a-strong-password>" -ForegroundColor Yellow
} else {
  Write-Host "        admin user(s) already exist ($adminCount) - nothing changed"
}
& $py seed.py

Pop-Location

# --- 2. Frontend ------------------------------------------------------------
try { $null = Get-Command npm -ErrorAction Stop; $hasNpm = $true } catch { $hasNpm = $false }
if ($hasNpm) {
  Write-Host "==> [5/5] Frontend: installing dependencies"
  Push-Location frontend
  npm install --no-fund --no-audit
  Pop-Location
} else {
  Write-Host "==> [5/5] Frontend: SKIPPED (npm not found - install Node 18+)" -ForegroundColor Yellow
}

# --- 3. Done ----------------------------------------------------------------
Write-Host @"

============================================================
 Setup complete! To run the app, open TWO terminals:

   Terminal 1 (API):
     cd backend
     .venv\Scripts\activate
     python -m uvicorn main:app --reload --port 8000

   Terminal 2 (web app):
     cd frontend
     npm run dev

 Then open  http://localhost:5173
   Admin login:  admin / changeme123   (change it - see above)
   Track demo:   PCL085263034594XYZ
============================================================
"@ -ForegroundColor Green
