from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from routers import analyze, offer
# ✅ Supprimer l'indexation automatique
# from scripts.index_knowledge_base import index_knowledge_base

# ✅ Ajouter le watcher
from services.minio_watcher import MinioWatcher

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

# ✅ Watcher global
watcher = None


@app.on_event("startup")
async def startup_event():
    """
    Démarre le backend et le watcher MinIO
    """
    global watcher
    
    logger.info("🚀 Démarrage du backend DIGIFLOW...")
    
    # ✅ Démarrer le watcher MinIO (surveillance automatique)
    try:
        watcher = MinioWatcher(check_interval=30)  # Vérifie toutes les 30s
        watcher.start()
        logger.info("📂 Watcher MinIO démarré")
    except Exception as e:
        logger.error(f"⚠️ Erreur de démarrage du watcher: {e}")
    
    logger.info("✅ Backend prêt !")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Arrête le watcher proprement
    """
    global watcher
    if watcher:
        watcher.stop()
        logger.info("⏹️ Watcher MinIO arrêté")


@app.get("/health")
async def health_check():
    """Vérifie l'état du serveur"""
    return {
        "status": "ok",
        "model": os.getenv("LLM_MODEL", "qwen2.5:7b"),
        "ingestion": "active",
        "watcher": "running" if watcher and watcher.running else "stopped",
        "version": "1.0.0"
    }