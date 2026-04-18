from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from .database import Base

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
    expiry = Column(Date)
    unit = Column(String(50))
    stock_qty = Column(Integer, default=0)