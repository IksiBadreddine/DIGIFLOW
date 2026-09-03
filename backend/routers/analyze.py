# backend/routers/analyze.py

import os
import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio 

from ingestion import DocumentProcessor
from services.llm_service import extract_requirements, match_product_compliance
from services.vector_store import VectorStore
from services.storage_service import StorageService
from services.document_service import DocumentService
from services.product_service import ProductService  # ✅ AJOUTER

router = APIRouter()
logger = logging.getLogger(__name__)

class MatchRequest(BaseModel):
    requirements: List[dict]
    products: List[dict]


@router.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyse un document uploadé avec matching parallèle
    """
    logger.info(f"📄 Analyse du fichier: {file.filename}")
    
    # 1. Initialiser les services
    storage = StorageService()
    doc_service = DocumentService()
    processor = DocumentProcessor()
    vector_store = VectorStore()
    product_service = ProductService()
    
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
        
        collection_name = f"cdc_{session_id}"
        try:
            # Supprimer l'ancienne collection si elle existe
            vector_store.delete_collection(collection_name)
        except:
            pass

        for chunk in doc.chunks:
            try:
                vector_store.add_document(
                    content=chunk.content,
                    metadata={
                        "document_id": str(doc_id),  # ✅ Convertir en string
                        "document_type": doc.document_type.value,
                        "filename": doc.filename,
                        "chunk_index": chunk.metadata.get("chunk_index", 0),
                        "session_id": session_id,
                        "source": "upload"
                    },
                    collection=collection_name
                )
            except Exception as e:
                logger.warning(f"Erreur d'indexation d'un chunk: {e}")
        
        # 8. Extraire les exigences avec le LLM
        requirements_result = extract_requirements(doc.full_text)
        requirements = requirements_result.get("requirements", [])
        logger.info(f"✅ {len(requirements)} exigences extraites")
        
        # 9. Récupérer le catalogue depuis PostgreSQL
        products = product_service.get_all_products()
        logger.info(f"✅ {len(products)} produits chargés depuis PostgreSQL")
        
        # 10. Recherche dans ChromaDB pour le contexte RAG
        context_docs = []
        if requirements:
            query = " ".join([req.get("description", "") for req in requirements])
            logger.info(f"🔍 Recherche RAG: {query[:100]}...")
            
            context_results = vector_store.search(
                query=query,
                collection="knowledge_base",
                n_results=10
            )
            
            for r in context_results:
                context_docs.append({
                    "content": r.get("content", ""),
                    "metadata": r.get("metadata", {})
                })
            
            logger.info(f"✅ {len(context_docs)} documents trouvés dans ChromaDB")
        
        # 11. ✅ MATCHING PAR LOTS DE 2
        logger.info(f"🧠 Lancement du matching pour {len(products)} produits")

        # ✅ Fonction de matching asynchrone
        async def match_product_async(product):
            try:
                product_dict = {
                    "id": product.get("product_id", product.get("id")),
                    "name": product.get("name", ""),
                    "manufacturer": product.get("manufacturer", ""),
                    "reference": product.get("reference", ""),
                    "category": product.get("category", ""),
                    "specs": product.get("specs", {}),
                    "tags": product.get("tags", []),
                    "datasheet_summary": product.get("datasheet_summary", "")
                }
                
                loop = asyncio.get_event_loop()
                match_result = await loop.run_in_executor(
                    None,
                    match_product_compliance,
                    requirements,
                    product_dict,
                    context_docs
                )
                
                # ✅ DÉTECTION DES INCOMPATIBILITÉS
                incompatibilities = []
                compliance_rows = match_result.get("compliance_rows", [])
                
                for row in compliance_rows:
                    if row.get("status") == "NON_CONFORME":
                        # Déterminer la sévérité
                        severity = "critique"
                        if "option" in row.get("requirement_text", "").lower() or "peut" in row.get("remarks", "").lower():
                            severity = "majeure"
                        
                        incompatibilities.append({
                            "requirement_id": row.get("requirement_id"),
                            "requirement_text": row.get("requirement_text"),
                            "specified_value": row.get("specified_value"),
                            "product_response": row.get("product_response"),
                            "severity": severity,
                            "reason": row.get("remarks", "Le produit ne répond pas à cette exigence")
                        })
                
                # ✅ SUGGESTION D'ALTERNATIVES
                alternatives = []
                if incompatibilities:
                    # Récupérer les produits alternatifs (tous sauf le produit courant)
                    other_products = [p for p in products if p.get("product_id") != product.get("product_id")]
                    
                    for alt_product in other_products[:3]:  # Limiter à 3 alternatives
                        try:
                            alt_dict = {
                                "id": alt_product.get("product_id", alt_product.get("id")),
                                "name": alt_product.get("name", ""),
                                "manufacturer": alt_product.get("manufacturer", ""),
                                "reference": alt_product.get("reference", ""),
                                "specs": alt_product.get("specs", {}),
                                "tags": alt_product.get("tags", [])
                            }
                            
                            # Vérifier si l'alternative répond aux exigences non conformes
                            alt_result = await loop.run_in_executor(
                                None,
                                match_product_compliance,
                                incompatibilities[:5],  # Seulement les incompatibilités
                                alt_dict,
                                []
                            )
                            
                            alt_score = alt_result.get("compliance_score", 0)
                            
                            if alt_score >= 0.6:  # Seuil pour proposer comme alternative
                                alternatives.append({
                                    "product_id": alt_product.get("product_id"),
                                    "product_name": alt_product.get("name"),
                                    "manufacturer": alt_product.get("manufacturer"),
                                    "reference": alt_product.get("reference"),
                                    "compliance_score": alt_score,
                                    "why": f"Ce produit répond à {len([r for r in alt_result.get('compliance_rows', []) if r.get('status') == 'CONFORME'])} exigences non conformes"
                                })
                        except Exception as e:
                            logger.warning(f"Erreur d'alternative pour {alt_product.get('name')}: {e}")
                    
                    # Trier par score
                    alternatives.sort(key=lambda x: x.get("compliance_score", 0), reverse=True)
                    alternatives = alternatives[:2]  # Top 2 alternatives
                
                return {
                    "product_id": match_result.get("product_id", product_dict.get("id")),
                    "product_name": match_result.get("product_name", product_dict.get("name")),
                    "manufacturer": match_result.get("manufacturer", product_dict.get("manufacturer")),
                    "reference": match_result.get("reference", product_dict.get("reference")),
                    "compliance_score": match_result.get("compliance_score", 0.5),
                    "compliance_rows": compliance_rows,
                    "strengths": match_result.get("strengths", ["Produit disponible"]),
                    "gaps": match_result.get("gaps", ["Vérification requise"]),
                    "incompatibilities": incompatibilities,  # ✅ AJOUTÉ
                    "alternatives": alternatives  # ✅ AJOUTÉ
                }
                
            except Exception as e:
                logger.warning(f"Erreur de matching: {e}")
                return {
                    "product_id": product.get("product_id"),
                    "product_name": product.get("name"),
                    "manufacturer": product.get("manufacturer"),
                    "reference": product.get("reference"),
                    "compliance_score": 0.3,
                    "compliance_rows": [],
                    "strengths": ["Produit disponible"],
                    "gaps": ["Erreur de matching"],
                    "incompatibilities": [],  # ✅ AJOUTÉ
                    "alternatives": []  # ✅ AJOUTÉ
                }

        # ✅ Traiter par lots de 2
        # ✅ Traiter par lots de 2
        batch_size = 2
        all_matched = []

        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            logger.info(f"📦 Lot {i//batch_size + 1}: {len(batch)} produits")
            
            tasks = [match_product_async(p) for p in batch]
            results = await asyncio.gather(*tasks)
            all_matched.extend(results)
            
            # Pause entre les lots
            if i + batch_size < len(products):
                logger.info("⏳ Pause de 1s...")
                await asyncio.sleep(1)

        matched_products = all_matched

        # ✅ CORRECTION : FORCER LE SCORE À 0 POUR LES PRODUITS SANS EXIGENCES APPLICABLES
        # ============================================================
        for product in matched_products:
            compliance_rows = product.get('compliance_rows', [])
            applicable_rows = [r for r in compliance_rows if r.get('status') != 'NON_APPLICABLE']
            
            if not applicable_rows:
                # ✅ AUCUNE EXIGENCE APPLICABLE → SCORE = 0%
                logger.info(f"⚠️ Aucune exigence applicable pour {product.get('product_name')} → Score forcé à 0%")
                product["compliance_score"] = 0.0
                product["strengths"] = ["Produit disponible dans le catalogue"]
                product["gaps"] = ["Aucune exigence ne correspond à ce type de produit"]
            else:
                # ✅ RECALCULER LE SCORE SI BESOIN (le LLM l'a déjà fait, mais on vérifie)
                total_score = sum(r.get('score', 0) for r in applicable_rows)
                calculated_score = total_score / len(applicable_rows)
                # Si le score du LLM est différent, on le corrige
                if abs(product.get("compliance_score", 0) - calculated_score) > 0.01:
                    logger.info(f"🔄 Correction du score pour {product.get('product_name')}: {product.get('compliance_score')} → {calculated_score}")
                    product["compliance_score"] = calculated_score

        # Trier par score
        matched_products.sort(key=lambda x: x.get("compliance_score", 0), reverse=True)

        # ============================================================
        # 🔍 LOG DE LA RÉPONSE DU BACKEND
        # ============================================================
        logger.info("=" * 60)
        logger.info("📤 RÉPONSE DU BACKEND AU FRONTEND")
        logger.info("=" * 60)
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Produits matchés: {len(matched_products)}")

        for idx, p in enumerate(matched_products):
            logger.info(f"\n📦 Produit {idx+1}: {p.get('product_name', 'N/A')}")
            logger.info(f"   Score: {p.get('compliance_score', 0)}")
            logger.info(f"   Référence: {p.get('reference', 'N/A')}")
            
            # Compter les statuts
            rows = p.get('compliance_rows', [])
            applicable = [r for r in rows if r.get('status') != 'NON_APPLICABLE']
            conformes = [r for r in applicable if r.get('status') == 'CONFORME']
            logger.info(f"   Statuts: {len(conformes)} CONFORME, {len(applicable) - len(conformes)} non CONFORME, {len(rows) - len(applicable)} NON_APPLICABLE")
            
            for row in rows[:4]:  # Afficher les 4 premières lignes
                logger.info(f"      {row.get('requirement_id')}: {row.get('product_response', 'N/A')[:50]} → {row.get('status')}")

        logger.info("=" * 60)
        
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
                "recommended_products": matched_products  # ✅ DOIT EXISTER
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
    
    # Fermer les connexions
    doc_service.close()
    product_service.close()

@router.get("/api/products")
async def get_products():
    """
    Récupère le catalogue produits depuis PostgreSQL
    """
    try:
        product_service = ProductService()
        products = product_service.get_all_products()
        product_service.close()
        
        return JSONResponse({
            "products": products,
            "count": len(products),
            "success": True,
            "source": "postgresql"
        })
        
    except Exception as e:
        logger.error(f"Erreur de récupération du catalogue: {e}")
        
        # Fallback sur JSON
        import json
        catalog_path = os.getenv("CATALOG_PATH", "data/products/catalog.json")
        
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
                    products = catalog.get("products", [])
                    return JSONResponse({
                        "products": products,
                        "count": len(products),
                        "success": True,
                        "source": "json_fallback"
                    })
            except Exception as e2:
                pass
        
        return JSONResponse({
            "products": [],
            "count": 0,
            "success": False,
            "error": str(e)
        })

@router.post("/api/match")
async def match_products(request: MatchRequest):
    """
    Test du matching : reçoit des exigences et des produits, retourne les scores
    """
    requirements = request.requirements
    products = request.products
    
    if not requirements or not products:
        return JSONResponse({
            "error": "requirements et products sont requis"
        }, status_code=400)
    
    logger.info(f"🧠 Matching: {len(requirements)} exigences, {len(products)} produits")
    
    # ✅ Utiliser la vraie fonction de matching
    from services.llm_service import match_product_compliance
    
    results = []
    for product in products:
        try:
            # Convertir le produit si nécessaire
            product_dict = product if isinstance(product, dict) else product.__dict__
            
            result = match_product_compliance(
                requirements=requirements[:10],
                product=product_dict,
                context_docs=[]
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Erreur de matching: {e}")
            results.append({
                "product_id": product_dict.get("id", product_dict.get("product_id")),
                "product_name": product_dict.get("name", "Inconnu"),
                "manufacturer": product_dict.get("manufacturer", "Inconnu"),
                "compliance_score": 0.3,
                "compliance_rows": [],
                "strengths": ["Produit disponible"],
                "gaps": ["Erreur de matching"]
            })
    
    return JSONResponse({"results": results})