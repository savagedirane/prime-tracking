"""
Creates (or resets the password for) an admin user who can log into the
admin dashboard and receive a JWT.

Usage:
    python create_admin.py <username> <password>
    python create_admin.py                # defaults to admin / changeme123
"""
import sys

from database import Base, engine, SessionLocal
import models
import auth

Base.metadata.create_all(bind=engine)


def run(username: str, password: str):
    db = SessionLocal()
    try:
        existing = db.query(models.AdminUser).filter(models.AdminUser.username == username).first()
        if existing:
            existing.password_hash = auth.hash_password(password)
            db.commit()
            print(f"Updated password for existing admin user '{username}'")
        else:
            db.add(models.AdminUser(username=username, password_hash=auth.hash_password(password)))
            db.commit()
            print(f"Created admin user '{username}'")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        run(sys.argv[1], sys.argv[2])
    else:
        print("No username/password given — creating default admin / changeme123")
        print("Change this password before deploying anywhere real.")
        run("admin", "changeme123")
