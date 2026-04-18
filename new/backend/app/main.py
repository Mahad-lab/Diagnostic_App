from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, patients, visits, stock, icd
import uvicorn

app = FastAPI(title="Medical Camp EMR - FastAPI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth, prefix="/auth", tags=["auth"])
app.include_router(patients, prefix="/patients", tags=["patients"])
app.include_router(visits, prefix="/visits", tags=["visits"])
app.include_router(stock, prefix="/stock", tags=["stock"])
app.include_router(icd, prefix="/icd", tags=["icd"])

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)