import os
import sys
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# Ensure backend root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import get_db, Base, engine
from routes.auth import router as auth_router
from routes.connections import router as connections_router
from routes.csv_upload import router as csv_router
from routes.chat import router as chat_router
from routes.dashboard import router as dashboard_router
from routes.bookmarks import router as bookmarks_router
from routes.analytics import router as analytics_router

app = FastAPI(
    title="Agentic Text-to-SQL Analyst API",
    description="Backend API for multi-step agentic text-to-SQL data analyst with self-correction, safe execution, and analytics",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(connections_router)
app.include_router(csv_router)
app.include_router(chat_router)
app.include_router(dashboard_router)
app.include_router(bookmarks_router)
app.include_router(analytics_router)

from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

@app.exception_handler(OperationalError)
async def db_operational_error_handler(request, exc: OperationalError):
    """Provide clear, actionable error feedback when database is unreachable."""
    import logging
    logging.getLogger("uvicorn.error").error(f"Database operational error: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Database connection error: Unable to connect to the database. "
                "If using PostgreSQL/Docker, please ensure Docker Desktop is running and run: "
                "'docker compose up -d app_db'. "
                "Alternatively, you can set DATABASE_URL=sqlite:///./app.db in .env for local SQLite mode."
            )
        }
    )

@app.on_event("startup")
def startup_event():
    """Ensure database tables and pgvector extension are initialized on startup."""
    import logging
    logger = logging.getLogger("uvicorn.error")
    try:
        from models import models  # noqa: F401
        with engine.connect() as conn:
            if not str(engine.url).startswith("sqlite"):
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection verified and application tables initialized successfully.")
    except Exception as e:
        logger.error(
            "\n" + "=" * 70 + "\n"
            "DATABASE CONNECTION ERROR ON STARTUP!\n"
            f"Could not connect to database at: {engine.url}\n"
            f"Details: {e}\n\n"
            "HOW TO FIX:\n"
            "  Option 1 (Recommended): Start Docker Desktop and run:\n"
            "    docker compose up -d app_db\n\n"
            "  Option 2 (Standalone SQLite): In your .env file, set:\n"
            "    DATABASE_URL=sqlite:///./app.db\n"
            + "=" * 70 + "\n"
        )

@app.get("/")
def root():
    return {
        "name": "Agentic Text-to-SQL Analyst API",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint checking application and database connection."""
    db_status = "connected"
    vector_status = "unknown"
    try:
        # Check basic DB query
        db.execute(text("SELECT 1"))
        # Check pgvector extension availability
        res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
        vector_status = "installed" if res else "missing"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if "unhealthy" not in db_status else "degraded",
        "database": db_status,
        "pgvector": vector_status,
        "embedding_model": settings.EMBEDDING_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
