# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routes.health import router as health_router
from app.routes.novelty import router as novelty_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 NOVELTYNET starting...")
    yield
    # Shutdown
    print("🛑 NOVELTYNET shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS — keep open for frontend / demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health_router, tags=["health"])
app.include_router(
    novelty_router,
    prefix=settings.API_PREFIX,
    tags=["novelty"]
)
