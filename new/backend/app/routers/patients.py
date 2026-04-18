from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Patient
from ..schemas import PatientCreate

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = Patient(
        patient_name=patient.patient_name,
        cnic=patient.cnic,
        nationality=patient.nationality,
        address=patient.address,
        phone=patient.phone,
        gender=patient.gender,
        age=patient.age,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return {"patient_id": db_patient.patient_id, "patient_name": db_patient.patient_name}

@router.get("/")
def get_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    patients = db.query(Patient).offset(skip).limit(limit).all()
    return patients

@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.put("/{patient_id}")
def update_patient(patient_id: int, patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db_patient.patient_name = patient.patient_name
    db_patient.cnic = patient.cnic
    db_patient.nationality = patient.nationality
    db_patient.address = patient.address
    db_patient.phone = patient.phone
    db_patient.gender = patient.gender
    db_patient.age = patient.age
    db.commit()
    db.refresh(db_patient)
    return db_patient

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    db_patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(db_patient)
    db.commit()
    return None