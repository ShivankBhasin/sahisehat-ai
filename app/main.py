from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.voice import router as voice_router
from app.core.config import settings
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print(f"{settings.app_name} starting...")
    print(f"Environment: {settings.app_env}")
    print(f"Gemini model: {settings.gemini_model}")
    print("=" * 50)

    yield

    print(f"{settings.app_name} shutting down...")

app = FastAPI(
    title="SahiSehat AI API",
    description=(
        "Multilingual AI health-support service "
        "for the SahiSehat platform."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.mount(
    "/generated_audio",
    StaticFiles(directory="generated_audio"),
    name="generated_audio",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(voice_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "model": settings.gemini_model,
    }