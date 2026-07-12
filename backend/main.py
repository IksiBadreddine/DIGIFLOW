from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from routers import analyze, offer
from scripts.index_knowledge_base import index_knowledge_base

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DIGIFLOW API",
    description="API pour l'analyse et la génération d'offres techniques",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(analyze.router)
app.include_router(offer.router)


@app.on_event("startup")
async def startup_event():
    """
    Indexe la base de connaissances au démarrage
    """
    logger.info("🚀 Démarrage du backend DIGIFLOW...")
    
    # Indexer la base de connaissances
    try:
        count = index_knowledge_base()
        logger.info(f"📚 Base de connaissances: {count} documents indexés")
    except Exception as e:
        logger.error(f"⚠️ Erreur d'indexation: {e}")
    
    logger.info("✅ Backend prêt !")


@app.get("/health")
async def health_check():
    """Vérifie l'état du serveur"""
    return {
        "status": "ok",
        "model": os.getenv("LLM_MODEL", "qwen2.5:7b"),
        "ingestion": "active",
        "version": "1.0.0"
    }