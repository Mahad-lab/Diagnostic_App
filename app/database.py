"""
Database configuration and ORM models for Medical Camp EMR (PostgreSQL + SQLAlchemy 2.0)
"""

from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Date, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import func
import streamlit as st
import os

Base = declarative_base()


# ========================= ORM MODELS =========================

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_name = Column(String(255), nullable=False)
    cnic = Column(String(20))
    nationality = Column(String(100))
    address = Column(Text)
    phone = Column(String(20))
    gender = Column(String(10))
    age = Column(Integer)


class Visit(Base):
    __tablename__ = "visits"

    visit_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id", ondelete="CASCADE"))
    doctor_type = Column(String(100))
    visit_date = Column(DateTime, server_default=func.now())
    history = Column(Text)
    bp = Column(String(20))
    heart_rate = Column(Integer)
    sat_o2 = Column(Float)
    temp = Column(Float)
    rr = Column(Integer)
    blood_glucose = Column(Float)
    gender = Column(String(10))
    age = Column(Integer)
    symptoms = Column(Text)
    indications = Column(Text)
    medicines = Column(Text)
    dispensed = Column(String(10), default="No")
    dispensed_details = Column(Text)


class Stock(Base):
    __tablename__ = "stock"

    key = Column(String(255), primary_key=True)
    generic = Column(String(255), nullable=False)
    brand = Column(String(255))
    dosage_form = Column(String(255))
    dose = Column(String(100))
    expiry = Column(Date, nullable=True)
    unit = Column(String(50))
    stock_qty = Column(Integer, default=0)


# ========================= ENGINE & SESSION =========================

def _get_database_url() -> str:
    try:
        if "database" in st.secrets:
            db = st.secrets["database"]
            return (
                f"postgresql://{db['user']}:{db['password']}"
                f"@{db['host']}:{db.get('port', 5432)}/{db['dbname']}"
            )
    except Exception:
        pass
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/emr_system",
    )


@st.cache_resource(show_spinner="Connecting to database...")
def get_engine():
    """Cached SQLAlchemy engine with connection pooling."""
    url = _get_database_url()
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
    )


@st.cache_resource
def _get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


@contextmanager
def get_db():
    """Context manager for a scoped database session."""
    db: Session = _get_session_factory()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they do not exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.commit()
    except Exception:
        pass  # pg_trgm requires superuser; optional
