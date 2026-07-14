# backend/routers/analyze.py

import os
import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List

from ingestion import DocumentProcessor
from services.llm_service import extract_requirements, match_product_compliance
from services.vector_store import VectorStore
from services.storage_service import StorageService
from services.document_service import DocumentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyse un document uploadé :
    1. Sauvegarde dans MinIO + PostgreSQL
    2. Ingestion et indexation dans ChromaDB
    3. Extraction des exigences avec LLM
    4. Matching avec les produits du catalogue
    """
    logger.info(f"📄 Analyse du fichier: {file.filename}")
    
    # 1. Initialiser les services
    storage = StorageService()
    doc_service = DocumentService()
    processor = DocumentProcessor()
    vector_store = VectorStore()
    
    # 2. Sauvegarder le fichier temporairement
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        # 3. Sauvegarder le fichier
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 4. Ingérer le document
        doc = processor.process_file(file_path)
        
        if not doc or doc.status.value == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Erreur d'ingestion: {doc.error if doc else 'Document non reconnu'}"
            )
        
        logger.info(f"✅ Document ingéré: {doc.document_type.value}")
        logger.info(f"   - Chunks: {len(doc.chunks)}")
        logger.info(f"   - Texte: {len(doc.full_text)} caractères")
        
        # 5. Upload vers MinIO
        minio_path = f"uploads/session_{os.urandom(8).hex()}/{file.filename}"
        storage.upload_bytes(content, minio_path)
        logger.info(f"✅ Document uploadé vers MinIO: {minio_path}")
        
        # 6. Sauvegarder dans PostgreSQL
        session_id = f"session_{os.urandom(8).hex()}"
        doc_id = doc_service.save_document(
            doc=doc,
            file_content=content,
            minio_path=minio_path,
            category="uploads",
            session_id=session_id
        )
        logger.info(f"✅ Document sauvegardé dans PostgreSQL: {doc_id}")
        
        # 7. Indexer dans ChromaDB
        for chunk in doc.chunks:
            try:
                vector_store.add_document(
                    content=chunk.content,
                    metadata={
                        "document_id": str(doc_id), 
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
        
        # 8. Extraire les exigences avec le LLM
        requirements_result = extract_requirements(doc.full_text)
        requirements = requirements_result.get("requirements", [])
        logger.info(f"✅ {len(requirements)} exigences extraites")
        
        # 9. Charger le catalogue produits
        catalog_path = "data/products/catalog.json"
        products = []
        if os.path.exists(catalog_path):
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
                products = catalog.get("products", [])
        
        # 10. Rechercher des documents pertinents dans la base de connaissances
        # pour enrichir le matching
        context_docs = []
        if requirements:
            # Prendre les 3 premières exigences pour la recherche
            query = " ".join([req.get("description", "") for req in requirements[:3]])
            context_results = vector_store.search(query, collection="knowledge_base", n_results=3)
            context_docs = [{"content": r.get("content", ""), "metadata": r.get("metadata", {})} for r in context_results]
        
        # 11. Match les produits avec les exigences
        matched_products = []
        for product in products:
            try:
                # Simuler un matching pour l'instant
                # Dans une vraie implémentation, on utiliserait l'IA
                match_result = match_product_compliance(
                    requirements=requirements[:10],
                    product=product,
                    context_docs=context_docs[:3] if context_docs else []
                )
                
                matched_products.append({
                    "product_id": product.get("id"),
                    "product_name": product.get("name"),
                    "manufacturer": product.get("manufacturer"),
                    "reference": product.get("reference"),
                    "compliance_score": match_result.get("compliance_score", 0.5),
                    "compliance_rows": match_result.get("compliance_rows", []),
                    "strengths": match_result.get("strengths", ["Compatible"]),
                    "gaps": match_result.get("gaps", [])
                })
            except Exception as e:
                logger.warning(f"Erreur de matching pour {product.get('name')}: {e}")
                # Fallback: score aléatoire
                matched_products.append({
                    "product_id": product.get("id"),
                    "product_name": product.get("name"),
                    "manufacturer": product.get("manufacturer"),
                    "reference": product.get("reference"),
                    "compliance_score": 0.5,
                    "compliance_rows": [],
                    "strengths": ["Produit disponible"],
                    "gaps": ["Vérification requise"]
                })
        
        # Trier par score
        matched_products.sort(key=lambda x: x.get("compliance_score", 0), reverse=True)
        
        # 12. Construire la réponse
        return JSONResponse({
            "session_id": session_id,
            "analysis": {
                "document_name": doc.filename,
                "document_type": doc.document_type.value,
                "extracted_requirements": requirements,
                "summary": requirements_result.get("summary", ""),
                "key_constraints": requirements_result.get("key_constraints", []),
                "chunks_count": len(doc.chunks),
                "characters_count": len(doc.full_text),
                "recommended_products": matched_products[:5]  # Top 5 produits
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
    
    # Fermer la connexion PostgreSQL
    doc_service.close()


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
    
    result = []
    for name in collections:
        info = vector_store.get_collection_info(name)
        result.append(info)
    
    return JSONResponse({
        "collections": result,
        "count": len(result)
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