import logging
import logging.config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from .core.config import get_settings
from .db.session import engine, Base
from .core.scheduler import start_scheduler
from .api import auth, detect, users, plans, progress, badges, notifications, admin

settings = get_settings()

# Configure structured logging
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        }
    },
    "root": {
        "handlers": ["console"],
        "level": settings.log_level
    }
}
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.debug and "/docs",
    redoc_url=settings.debug and "/redoc",
    openapi_url="/openapi.json"
)

# Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts or ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Startup and shutdown events
@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Application startup in %s mode", settings.environment)
    start_scheduler()

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Application shutdown")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check
@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(plans.router, prefix="/api/v1/plans", tags=["plans"])
app.include_router(progress.router, prefix="/api/v1/progress", tags=["progress"])
app.include_router(badges.router, prefix="/api/v1/badges", tags=["badges"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(detect.router, prefix="/api/v1/detect", tags=["detect"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# Root endpoint
@app.get("/", include_in_schema=False)
def root():
    return {"message": "Welcome to the Gym Equipment Detection API"}
