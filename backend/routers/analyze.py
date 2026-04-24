"""
Analysis Router
POST /api/analyze  — Upload CdC, extract requirements, match products
"""
import os
import uuid
import json
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from services.ingestion import extract_text, chunk_text, load_product_catalog
from services.vector_store import index_products, index_cdc, search_products
from services.llm_service import extract_requirements, match_product_compliance
from models.schemas import (
    AnalysisResult, Requirement, ProductMatch, ComplianceRow, ConformityStatus
)

router = APIRouter(prefix="/api", tags=["analysis"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CATALOG_PATH = "./data/products/catalog.json"

# In-memory session store (use Redis in production)
sessions: dict = {}


def ensure_product_index():
    """Index product catalog on first call if not already done."""
    marker = Path(CHROMA_DIR) / ".products_indexed"
    if marker.exists():
        return
    docs, _ = load_product_catalog(CATALOG_PATH)
    index_products(docs, CHROMA_DIR)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Upload a CdC (PDF/DOCX/TXT), extract requirements,
    match against product catalog, return structured analysis.
    """
    # Validate file type
    allowed = {".pdf", ".docx", ".txt"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Format non supporté: {ext}. Acceptés: {', '.join(allowed)}")

    # Save uploaded file
    session_id = str(uuid.uuid4())[:8]
    upload_path = Path(UPLOAD_DIR) / f"{session_id}_{file.filename}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    if len(content) > int(os.getenv("MAX_FILE_SIZE_MB", 20)) * 1024 * 1024:
        raise HTTPException(400, "Fichier trop volumineux (max 20 MB)")

    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        # 1. Extract text
        text = extract_text(str(upload_path))
        if len(text.strip()) < 50:
            raise HTTPException(422, "Impossible d'extraire le texte du document.")

        # 2. Index CdC in ChromaDB
        chunks = chunk_text(text, file.filename)
        index_cdc(chunks, CHROMA_DIR, session_id)

        # 3. Ensure product catalog is indexed
        ensure_product_index()

        # 4. Extract requirements with GPT-4
        extracted = extract_requirements(text)
        requirements_raw = extracted.get("requirements", [])
        summary = extracted.get("summary", "")
        constraints = extracted.get("key_constraints", [])

        # 5. Load product catalog
        _, products = load_product_catalog(CATALOG_PATH)

        # 6. For each product, compute compliance
        product_matches = []
        for product in products:
            # RAG: retrieve relevant context for this product
            context_docs = search_products(
                query=f"{product['name']} {product['reference']} specifications techniques",
                persist_dir=CHROMA_DIR,
                k=3,
            )

            match_data = match_product_compliance(
                requirements=requirements_raw,
                product=product,
                context_docs=context_docs,
            )

            rows = [
                ComplianceRow(
                    requirement_id=r.get("requirement_id", ""),
                    requirement_text=r.get("requirement_text", ""),
                    specified_value=r.get("specified_value"),
                    product_response=r.get("product_response", ""),
                    status=ConformityStatus(r.get("status", "NON_VERIFIE")),
                    remarks=r.get("remarks"),
                )
                for r in match_data.get("compliance_rows", [])
            ]

            product_matches.append(ProductMatch(
                product_id=product["id"],
                product_name=product["name"],
                manufacturer=product["manufacturer"],
                reference=product["reference"],
                compliance_score=match_data.get("compliance_score", 0.0),
                compliance_rows=rows,
                strengths=match_data.get("strengths", []),
                gaps=match_data.get("gaps", []),
            ))

        # Sort by compliance score descending
        product_matches.sort(key=lambda x: x.compliance_score, reverse=True)

        # 7. Build final result
        result = AnalysisResult(
            document_name=file.filename,
            extracted_requirements=[
                Requirement(**r) for r in requirements_raw
            ],
            summary=summary,
            key_constraints=constraints,
            recommended_products=product_matches,
        )

        # Store session for offer generation
        sessions[session_id] = {
            "analysis": result.model_dump(),
            "summary": summary,
            "constraints": constraints,
            "products": [p.model_dump() for p in product_matches],
        }

        return JSONResponse({
            "session_id": session_id,
            "analysis": result.model_dump(),
        })

    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Erreur parsing réponse LLM: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Erreur d'analyse: {str(e)}")
    finally:
        # Clean up uploaded file
        if upload_path.exists():
            upload_path.unlink()


@router.get("/session/{session_id}")
def get_session(session_id: str):
    """Retrieve a previously computed analysis session."""
    if session_id not in sessions:
        raise HTTPException(404, "Session introuvable ou expirée")
    return sessions[session_id]
