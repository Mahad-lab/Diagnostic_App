from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Visit
from ..schemas import VisitCreate
from datetime import datetime

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_visit(visit: VisitCreate, db: Session = Depends(get_db)):
    db_visit = Visit(
        patient_id=visit.patient_id,
        doctor_type=visit.doctor_type,
        history=visit.history,
        bp=visit.bp,
        heart_rate=visit.heart_rate,
        sat_o2=visit.sat_o2,
        temp=visit.temp,
        rr=visit.rr,
        blood_glucose=visit.blood_glucose,
        symptoms=visit.symptoms,
        indications=visit.indications,
        medicines=visit.medicines,
    )
    db.add(db_visit)
    db.commit()
    db.refresh(db_visit)
    return {"visit_id": db_visit.visit_id, "patient_id": db_visit.patient_id}

@router.get("/")
def get_visits(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    visits = db.query(Visit).offset(skip).limit(limit).all()
    return visits

@router.get("/{visit_id}")
def get_visit(visit_id: int, db: Session = Depends(get_db)):
    visit = db.query(Visit).filter(Visit.visit_id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit

@router.get("/patient/{patient_id}")
def get_patient_visits(patient_id: int, db: Session = Depends(get_db)):
    visits = db.query(Visit).filter(Visit.patient_id == patient_id).all()
    return visits