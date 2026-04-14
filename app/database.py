# database.py
"""
Database configuration and session management for Medical Camp EMR (PostgreSQL + SQLAlchemy)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
import streamlit as st
import os
from typing import Generator

# Base for ORM models
Base = declarative_base()

# --------------------- Configuration ---------------------
def get_database_url() -> str:
    """Load PostgreSQL URL from Streamlit secrets (recommended) or environment variables."""
    if "database" in st.secrets:
        # Using Streamlit secrets.toml (best practice)
        db = st.secrets["database"]
        return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db.get('port', 5432)}/{db['dbname']}"
    else:
        # Fallback to environment variables
        return os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/emr_system"
        )


# Create engine with connection pooling (shared across the app)
@st.cache_resource(show_spinner="Connecting to PostgreSQL...")
def get_engine():
    url = get_database_url()
    engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=10,          # Adjust based on your traffic
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,     # Recycle connections every 30 min
        pool_pre_ping=True,    # Test connection before using
        echo=False             # Set True for debugging SQL
    )
    return engine


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """Dependency to get a database session (use with 'with' statement)."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize tables (run once)
def init_db():
    """Create all tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Optional: Add any initial data or indexes here
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))  # For better fuzzy search if needed
        conn.commit()


# Call init on import
init_db()