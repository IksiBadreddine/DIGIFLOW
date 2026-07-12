"""
Routeur pour l'analyse de documents - Version avec ingestion
"""

import os
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
    
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        # Sauvegarder le fichier
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. Utiliser le module d'ingestion
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
            try:
                vector_store.add_document(
                    content=chunk.content,
                    metadata={
                        "document_id": doc.id,
                        "document_type": doc.document_type.value,
                        "filename": doc.filename,
                        "chunk_index": chunk.metadata.get("chunk_index", 0),
                        "session_id": session_id,
                        "source": "upload"
                    },
                    collection=f"cdc_{session_id}"
                )
            except Exception as e:
                logger.warning(f"Erreur d'indexation d'un chunk: {e}")
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Erreur de nettoyage: {e}")

@router.get("/api/search")
async def search_knowledge(
    q: str,
    limit: int = 5,
    collection: str = "knowledge_base"
):
    """
    Recherche dans la base de connaissances
    """
    logger.info(f"🔍 Recherche: {q}")
    
    vector_store = VectorStore()
    results = vector_store.search(q, collection=collection, n_results=limit)
    
    if not results:
        return JSONResponse({
            "query": q,
            "results": [],
            "count": 0
        })
    
    # Formater les résultats
    formatted_results = []
    for result in results:
        formatted_results.append({
            "content": result.get("content", ""),
            "score": 1 - result.get("distance", 1) if result.get("distance") else 0,
            "metadata": result.get("metadata", {})
        })
    
    return JSONResponse({
        "query": q,
        "results": formatted_results,
        "count": len(formatted_results)
    })


@router.get("/api/collections")
async def list_collections():
    """
    Liste toutes les collections ChromaDB
    """
    vector_store = VectorStore()
    collections = vector_store.list_collections()
    
    # Récupérer les infos de chaque collection
    result = []
    for name in collections:
        info = vector_store.get_collection_info(name)
        result.append(info)
    
    return JSONResponse({
        "collections": result,
        "count": len(result)
    })


@router.post("/api/analyze/batch")
async def analyze_batch(files: list[UploadFile] = File(...)):
    """
    Analyse plusieurs documents en batch
    """
    logger.info(f"📄 Analyse batch de {len(files)} fichiers")
    
    results = []
    processor = DocumentProcessor()
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    for file in files:
        try:
            # Sauvegarder
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

@router.get("/api/products")
async def get_products():
    """
    Récupère le catalogue produits
    """
    import json
    catalog_path = os.getenv("CATALOG_PATH", "data/products/catalog.json")
    
    if not os.path.exists(catalog_path):
        return JSONResponse({
            "products": [],
            "count": 0,
            "error": "Catalogue non trouvé"
        })
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
            products = catalog.get("products", [])
            return JSONResponse({
                "products": products,
                "count": len(products),
                "success": True
            })
    except Exception as e:
        return JSONResponse({
            "products": [],
            "count": 0,
            "error": str(e)
        })