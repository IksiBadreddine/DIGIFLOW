"""
PresalesAI — FastAPI Backend
Plateforme IA de génération d'offres techniques (ELV/ICT/Telecom/Security)
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers.analyze import router as analyze_router
from routers.offer import router as offer_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure directories exist
    for d in [
        os.getenv("UPLOAD_DIR", "./uploads"),
        os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("✅ PresalesAI backend started")
    yield
    print("🛑 PresalesAI backend shutting down")


app = FastAPI(
    title="PresalesAI",
    description="Plateforme IA de génération d'offres techniques ICT/ELV/Telecom/Security",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(offer_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
    }
