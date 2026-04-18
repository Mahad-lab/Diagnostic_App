from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Stock

router = APIRouter()

@router.get("/")
def get_stock(db: Session = Depends(get_db)):
    stock = db.query(Stock).all()
    return stock

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_stock(item: dict, db: Session = Depends(get_db)):
    db_item = Stock(
        key=item["key"],
        generic=item["generic"],
        brand=item.get("brand"),
        dosage_form=item.get("dosage_form"),
        dose=item.get("dose"),
        expiry=item.get("expiry"),
        unit=item.get("unit"),
        stock_qty=item.get("stock_qty", 0),
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{key}")
def update_stock(key: str, item: dict, db: Session = Depends(get_db)):
    db_item = db.query(Stock).filter(Stock.key == key).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field in ["generic", "brand", "dosage_form", "dose", "expiry", "unit", "stock_qty"]:
        if field in item:
            setattr(db_item, field, item[field])
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock(key: str, db: Session = Depends(get_db)):
    db_item = db.query(Stock).filter(Stock.key == key).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return None