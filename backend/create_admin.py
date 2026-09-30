"""
Creates (or resets the password for) an admin user who can log into the
admin dashboard and receive a JWT.

Usage:
    python create_admin.py <username> <password> [role]
    python create_admin.py                # defaults to admin / changeme123

Roles: "admin" (full control, incl. delete/restore) or "operator"
(day-to-day work: create shipments, add milestones, edit details).

NOTE: create_all() below is a dev convenience — Alembic migrations are the
source of truth for the schema in production.
"""
import sys

from database import Base, engine, SessionLocal
import models
import auth

Base.metadata.create_all(bind=engine)

ROLES = ("admin", "operator")


def run(username: str, password: str, role: str = "admin"):
    if role not in ROLES:
        print(f"Invalid role '{role}' — must be one of {ROLES}")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(models.AdminUser).filter(models.AdminUser.username == username).first()
        if existing:
            existing.password_hash = auth.hash_password(password)
            existing.role = role
            db.commit()
            print(f"Updated existing user '{username}' (role={role})")
        else:
            db.add(models.AdminUser(username=username, password_hash=auth.hash_password(password), role=role))
            db.commit()
            print(f"Created user '{username}' (role={role})")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        role = sys.argv[3] if len(sys.argv) >= 4 else "admin"
        run(sys.argv[1], sys.argv[2], role)
    else:
        print("No username/password given — creating default admin / changeme123")
        print("Change this password before deploying anywhere real.")
        run("admin", "changeme123")
