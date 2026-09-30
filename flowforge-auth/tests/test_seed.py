"""Verify the seed script populates the database with sample data."""
from app import models, seed
from app.database import SessionLocal


def test_seed_populates_sample_users():
    seed.seed()
    db = SessionLocal()
    try:
        emails = {u.email for u in db.query(models.User).all()}
        assert "maria@flowforge.example" in emails
        assert db.query(models.User).count() >= 4
        assert db.query(models.LoginEvent).count() >= 1
    finally:
        db.close()
