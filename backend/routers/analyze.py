# backend/routers/analyze.py

import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from ingestion import DocumentProcessor
from services.llm_service import extract_requirements
from services.vector_store import VectorStore

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyse un document uploadé :
    1. Ingestion avec le module d'ingestion
    2. Extraction des exigences avec LLM
    3. Indexation dans ChromaDB
    """
    logger.info(f"📄 Analyse du fichier: {file.filename}")
    
    # 1. Sauvegarder le fichier temporairement
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{file.filename}")
    
    try:
        # Sauvegarder
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. ✅ UTILISER LE MODULE D'INGESTION
        processor = DocumentProcessor()
        doc = processor.process_file(file_path)
        
        if not doc or doc.status.value == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Erreur d'ingestion: {doc.error if doc else 'Document non reconnu'}"
            )
        
        logger.info(f"✅ Document ingéré: {doc.document_type.value}")
        logger.info(f"   - Chunks: {len(doc.chunks)}")
        logger.info(f"   - Texte: {len(doc.full_text)} caractères")
        
        # 3. Extraire les exigences avec le LLM
        requirements_result = extract_requirements(doc.full_text)
        
        # 4. Indexer dans ChromaDB
        vector_store = VectorStore()
        session_id = f"session_{os.urandom(8).hex()}"
        
        # Indexer les chunks du document
        for chunk in doc.chunks:
            vector_store.add_document(
                content=chunk.content,
                metadata={
                    "document_id": doc.id,
                    "document_type": doc.document_type.value,
                    "filename": doc.filename,
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    "session_id": session_id
                },
                collection=f"cdc_{session_id}"
            )
        
        logger.info(f"✅ Document indexé dans ChromaDB")
        
        # 5. Construire la réponse
        return JSONResponse({
            "session_id": session_id,
            "analysis": {
                "document_name": doc.filename,
                "document_type": doc.document_type.value,
                "extracted_requirements": requirements_result.get("requirements", []),
                "summary": requirements_result.get("summary", ""),
                "key_constraints": requirements_result.get("key_constraints", []),
                "chunks_count": len(doc.chunks),
                "characters_count": len(doc.full_text)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(file_path):
            os.unlink(file_path)


@router.post("/api/analyze/batch")
async def analyze_batch(files: list[UploadFile] = File(...)):
    """
    Analyse plusieurs documents en batch
    """
    results = []
    processor = DocumentProcessor()
    
    for file in files:
        try:
            # Sauvegarder
            upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, file.filename)
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Ingérer
            doc = processor.process_file(file_path)
            
            if doc and doc.status.value != "failed":
                results.append({
                    "filename": doc.filename,
                    "type": doc.document_type.value,
                    "chunks": len(doc.chunks),
                    "characters": len(doc.full_text),
                    "success": True
                })
            else:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": doc.error if doc else "Non reconnu"
                })
            
            # Nettoyer
            if os.path.exists(file_path):
                os.unlink(file_path)
                
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return JSONResponse({
        "total": len(files),
        "results": results
    })