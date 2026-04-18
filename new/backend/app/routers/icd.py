from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db

router = APIRouter()

@router.get("/")
def get_icd_codes(db: Session = Depends(get_db)):
    return []

@router.get("/{code}")
def get_icd_code(code: str, db: Session = Depends(get_db)):
    return {"code": code, "description": "Not found"}