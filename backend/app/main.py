"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import debate, politicians, rankings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB tables exist
    init_db()
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="누가 진짜 부자가 되었나?",
    description="국회의원 재산 분석 POC API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(rankings.router)
app.include_router(politicians.router)
app.include_router(debate.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "wealth-tracker"}
