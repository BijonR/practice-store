import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # Defaults to local SQLite so you can run this with zero setup.
    # Set DATABASE_URL in your .env to point at Postgres later (Oracle Cloud / Supabase / etc).
    _db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'store.db')}")
    # Some providers hand out "postgres://" but SQLAlchemy 1.4+ requires "postgresql://"
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID", "")

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB upload limit (for CSV bulk uploads)
