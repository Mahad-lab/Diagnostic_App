from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    role: str

class PatientCreate(BaseModel):
    patient_name: str
    cnic: Optional[str] = None
    nationality: str = "Pakistani"
    address: Optional[str] = None
    phone: Optional[str] = None
    gender: str
    age: int

class VisitCreate(BaseModel):
    patient_id: int
    doctor_type: str
    history: str
    bp: str
    heart_rate: int
    sat_o2: float
    temp: float
    rr: int
    blood_glucose: float
    symptoms: str
    indications: str
    medicines: str

# ... (more schemas for Stock, etc.)