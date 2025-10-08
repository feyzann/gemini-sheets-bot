"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.routes.chat import router as chat_router
from app.core.config import get_settings

settings = get_settings()

# Import logging setup
import app.core.logging

# Create FastAPI app
app = FastAPI(
    title="Gemini Sheets Bot",
    description="FastAPI backend for n8n integration with Gemini 2.5 Flash and Google Sheets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)

@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "service": "Gemini Sheets Bot",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "gemini-sheets-bot",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Gemini Sheets Bot...")
    logger.info(f"Port: {settings.port}")
    logger.info(f"Gemini Model: {settings.gemini_model}")
    logger.info(f"Sheet ID: {settings.sheet_id}")
    logger.info(f"Default Locale: {settings.default_locale}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Gemini Sheets Bot...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
        log_level="info"
    )
