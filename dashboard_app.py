import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from dashboard_database import client
from routers import dashboard_overview, dashboard_pages, recent_transactions

app = FastAPI(title="Dashboard API", version="1.0.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "DASHBOARD_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recent_transactions.router, prefix="/api")
app.include_router(dashboard_overview.router, prefix="/api")
app.include_router(dashboard_pages.router, prefix="/api")

@app.get("/")
def home():
    return {"message": "Dashboard API is running", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    try:
        client.admin.command("ping")
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error
    return {"status": "ok", "database": "connected"}
