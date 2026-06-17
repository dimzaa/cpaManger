"""
Main FastAPI application entry point.

Creates the FastAPI app, registers all routes, and starts the server.
"""

# Ensure UTF-8 console output on Windows so emoji / Hebrew in log lines don't
# crash the logging handler under code pages like cp1255.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.config import API_HOST, API_PORT, DEBUG
from backend.database import init_db, get_db
from backend.routes import upload, municipalities, runs, budget, auth, export, explanations, presets, suggestions, employees, reasons, positions, analytics
from backend.routes.deadlines import router as deadlines_router, init_deadlines
from backend.routes.reports import router as reports_router, init_reports
from backend.routes.reminders import router as reminders_router
from backend.routes.ministry import router as ministry_router
from backend.services.reminder_service import start_reminder_service, stop_reminder_service
from backend.utils.seed_ministry_deadlines import seed_ministry_deadlines
from backend.utils.seed_ministry_codes import seed_ministry_codes
from backend.services.report_scheduler import start_scheduler, stop_scheduler
from backend.services.pdf_generator import register_fonts
from backend.utils.seed_presets import seed_default_presets
from backend.utils.seed_reasons_library import seed_reasons_library
from backend.utils.migrate_users_table import migrate_users_table, migrate_budget_lines_table, migrate_ministry_codes_table, migrate_municipalities_table, migrate_monthly_runs_table
from backend.services.logger import get_logger

logger = get_logger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Education Budget Platform API")
    print(f"   Host: {API_HOST}:{API_PORT}")
    print(f"   Debug: {DEBUG}")
    logger.info("Application startup")
    
    # Initialize database
    try:
        init_db()
        
        # Run database migrations
        migrate_users_table()
        migrate_budget_lines_table()
        migrate_ministry_codes_table()
        migrate_municipalities_table()
        migrate_monthly_runs_table()
        
        # Seed default presets
        db = next(get_db())
        count = seed_default_presets(db)
        if count > 0:
            print(f"✅ Seeded {count} default preset explanations")
        
        # Seed reasons library
        seed_reasons_library()

        # Init deadline tables and seed ministry deadlines
        init_deadlines(db)

        # Init reports tables
        init_reports(db)

        # Seed and start reminder service
        seed_ministry_deadlines(db)

        # Seed ministry budget codes
        count_codes = seed_ministry_codes(db)
        if count_codes > 0:
            print(f"✅ Seeded {count_codes} ministry codes")

        # Register Hebrew fonts for PDF generation
        register_fonts()

        # Start auto-report scheduler
        start_scheduler()

        # Start reminder scheduler
        start_reminder_service(get_db)

        db.close()
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        logger.error(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down API")
    logger.info("Application shutdown")
    stop_scheduler()
    stop_reminder_service()


# Create FastAPI app
app = FastAPI(
    title="Education Budget Management Platform",
    description="API for managing ministry education budget files and municipality portals",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== ROUTES ==========

# Upload endpoint
app.include_router(upload.router)

# Municipality endpoints
app.include_router(municipalities.router)

# Monthly runs endpoints
app.include_router(runs.router)
app.include_router(runs.admin_router)

# Budget data endpoints
app.include_router(budget.router)

# Authentication endpoints
app.include_router(auth.router)

# Export and notification endpoints
app.include_router(export.router)

# Explanations endpoints
app.include_router(explanations.router)

# Preset explanations endpoints
app.include_router(presets.router)

# Explanation suggestions endpoints (submit, approve, reject)
app.include_router(suggestions.router)

# Employee management endpoints (admin only)
app.include_router(employees.router)

# Reasons library endpoints (CPA management of explanation reasons)
app.include_router(reasons.router)

# Positions & quotas analysis endpoints
app.include_router(positions.router)

# Reminders & Notifications endpoints
app.include_router(reminders_router)

# Ministry integration endpoints
app.include_router(ministry_router)

# Deadlines & application tracking endpoints
app.include_router(deadlines_router)

# Reports & documents endpoints
app.include_router(reports_router)

# Analytics & trends endpoints
app.include_router(analytics.router)


# ========== HEALTH CHECK ==========

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Education Budget Management Platform",
    }


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "service": "Education Budget Management Platform",
        "version": "0.1.0",
        "description": "API for managing ministry education budget files",
        "endpoints": {
            "health": "/health",
            "api_docs": "/docs",
            "upload": {
                "method": "POST",
                "path": "/api/upload",
                "description": "Upload Ministry budget files (ZIP format)"
            },
            "municipalities": {
                "method": "GET",
                "path": "/api/municipalities",
                "description": "List all municipalities"
            },
            "budget": {
                "method": "GET",
                "path": "/api/budget/{municipality_id}/{month}",
                "description": "Get budget data for a municipality in a specific month"
            },
        }
    }


# ========== ERROR HANDLERS ==========

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if DEBUG else "Unknown error"},
    )


# ========== STARTUP MESSAGES ==========

@app.on_event("startup")
async def startup_message():
    """Print startup messages."""
    print("\n" + "="*60)
    print("✅ Education Budget Management Platform API Ready")
    print("="*60)
    print(f"\n📚 API Documentation:")
    print(f"   http://{API_HOST}:{API_PORT}/docs    (Swagger UI)")
    print(f"   http://{API_HOST}:{API_PORT}/redoc   (ReDoc)")
    print(f"\n🔗 Main Endpoints:")
    print(f"   POST   /api/upload                    - Upload budget files")
    print(f"   GET    /api/municipalities            - List municipalities")
    print(f"   GET    /api/budget/{'{id}'}/{'{month}'}            - Get budget data")
    print(f"   GET    /health                       - Health check")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
    )
