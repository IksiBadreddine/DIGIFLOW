# backend/routers/offer.py

import os
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List, Optional

from ingestion import DocumentProcessor
from services.llm_service import match_product_compliance, generate_offer
from services.vector_store import VectorStore

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/generate-offer")
async def generate_technical_offer(
    session_id: str,
    selected_product_ids: Optional[List[str]] = None,
    use_all_products: bool = False
):
    """
    Génère une offre technique à partir des documents ingérés
    """
    logger.info(f"📋 Génération d'offre pour session: {session_id}")
    
    # 1. Récupérer les documents indexés
    vector_store = VectorStore()
    
    # Récupérer les chunks de la session
    collection_name = f"cdc_{session_id}"
    documents = vector_store.get_collection(collection_name)
    
    if not documents:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    
    # 2. Récupérer les exigences extraites (depuis la session)
    # (à implémenter avec une base de données)
    
    # 3. Matching des produits
    # (à implémenter avec le catalogue)
    
    # 4. Génération de l'offre
    # (à implémenter avec le LLM)
    
    return {
        "title": "Offre Technique",
        "reference": f"REF-{session_id[:8]}",
        "sections": [
            {"title": "1. Introduction", "content": "...", "source": "generated"},
            {"title": "2. Compréhension du Besoin", "content": "...", "source": "generated"},
        ],
        "boq": [],
        "compliance_table": [],
        "total_compliance_rate": 0.85,
        "documents_used": len(documents)
    }


@router.get("/api/export/{session_id}")
async def export_offer(session_id: str):
    """
    Exporte l'offre au format DOCX
    """
    # À implémenter avec python-docx
    pass