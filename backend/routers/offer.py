# backend/routers/offer.py

import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateOfferRequest(BaseModel):
    session_id: str
    selected_product_ids: Optional[List[str]] = None


@router.post("/api/generate-offer")
async def generate_offer(request: GenerateOfferRequest):
    """
    Génère une offre technique à partir des produits sélectionnés
    """
    logger.info(f"📋 Génération d'offre pour session: {request.session_id}")
    
    # Simuler une offre
    offer_data = {
        "title": "Offre Technique - Projet Client",
        "reference": f"REF-{request.session_id[:8].upper()}",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "sections": [
            {
                "title": "1. Introduction",
                "content": "Nous vous proposons une solution technique complète répondant à vos besoins."
            },
            {
                "title": "2. Compréhension du Besoin",
                "content": "Le système doit fournir une connectivité réseau fiable..."
            },
            {
                "title": "3. Solution Technique",
                "content": "La solution proposée comprend les équipements suivants..."
            }
        ],
        "boq": [
            {
                "pos": "1",
                "designation": "Switch Cisco CBS350-24P-4G",
                "reference": "CBS350-24P-4G",
                "manufacturer": "Cisco",
                "unit": "U",
                "quantity": 1,
                "unit_price_eur": 1500,
                "remarks": "Switch manageable 24 ports PoE+"
            }
        ],
        "compliance_table": [
            {
                "requirement_id": "REQ-001",
                "requirement_text": "Switch 24 ports PoE+",
                "specified_value": "24 ports PoE+",
                "product_response": "24 ports PoE+",
                "status": "CONFORME",
                "remarks": "OK"
            }
        ],
        "total_compliance_rate": 0.85,
        "selected_products": request.selected_product_ids or []
    }
    
    # Sauvegarder l'offre
    os.makedirs("data/offers", exist_ok=True)
    json_path = f"data/offers/{request.session_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(offer_data, f, ensure_ascii=False, indent=2)
    
    return JSONResponse(offer_data)


@router.get("/api/export/{session_id}")
async def export_offer(session_id: str):
    """
    Exporte l'offre au format DOCX
    """
    logger.info(f"📤 Export DOCX pour session: {session_id}")
    
    # 1. Récupérer les données de l'offre
    json_path = f"data/offers/{session_id}.json"
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Offre non trouvée")
    
    with open(json_path, "r", encoding="utf-8") as f:
        offer_data = json.load(f)
    
    # 2. Générer le DOCX
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        
        doc = Document()
        
        # ---- Page de titre ----
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run("OFFRE TECHNIQUE")
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.name = 'Arial'
        
        doc.add_paragraph()
        
        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = subtitle.add_run(offer_data.get("title", "Offre Technique"))
        run.font.size = Pt(18)
        run.font.name = 'Arial'
        
        doc.add_paragraph()
        doc.add_paragraph()
        
        ref = doc.add_paragraph()
        ref.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = ref.add_run(f"Référence : {offer_data.get('reference', 'REF-XXXX')}")
        run.font.size = Pt(12)
        run.font.name = 'Arial'
        
        date = doc.add_paragraph()
        date.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = date.add_run(f"Date : {offer_data.get('date', datetime.now().strftime('%d/%m/%Y'))}")
        run.font.size = Pt(12)
        run.font.name = 'Arial'
        
        doc.add_page_break()
        
        # ---- Sections ----
        for section in offer_data.get("sections", []):
            doc.add_heading(section.get("title", "Section"), level=1)
            doc.add_paragraph(section.get("content", ""))
            doc.add_paragraph()
        
        doc.add_page_break()
        
        # ---- BOQ ----
        doc.add_heading("BILL OF QUANTITIES (BOQ)", level=1)
        doc.add_paragraph()
        
        table = doc.add_table(rows=1, cols=7)
        table.style = 'Table Grid'
        
        # En-têtes
        headers = ["Pos.", "Désignation", "Référence", "Fabricant", "Unité", "Qté", "Remarques"]
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            # Rendre le texte gras
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.size = Pt(11)
                    run.font.name = 'Arial'
        
        # Données
        for item in offer_data.get("boq", []):
            row = table.add_row()
            row.cells[0].text = str(item.get("pos", ""))
            row.cells[1].text = item.get("designation", "")
            row.cells[2].text = item.get("reference", "")
            row.cells[3].text = item.get("manufacturer", "")
            row.cells[4].text = item.get("unit", "")
            row.cells[5].text = str(item.get("quantity", ""))
            row.cells[6].text = item.get("remarks", "")
            
            # Taille de police
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
                        run.font.name = 'Arial'
        
        doc.add_page_break()
        
        # ---- Tableau de conformité ----
        doc.add_heading("TABLEAU DE CONFORMITÉ", level=1)
        doc.add_paragraph()
        
        table2 = doc.add_table(rows=1, cols=6)
        table2.style = 'Table Grid'
        
        headers2 = ["ID", "Exigence", "Valeur Requise", "Réponse Produit", "Statut", "Remarques"]
        for i, header in enumerate(headers2):
            cell = table2.rows[0].cells[i]
            cell.text = header
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.size = Pt(11)
                    run.font.name = 'Arial'
        
        for item in offer_data.get("compliance_table", []):
            row = table2.add_row()
            row.cells[0].text = item.get("requirement_id", "")
            row.cells[1].text = item.get("requirement_text", "")
            row.cells[2].text = item.get("specified_value", "")
            row.cells[3].text = item.get("product_response", "")
            
            # ✅ Statut avec couleur
            status = item.get("status", "")
            cell_status = row.cells[4]
            cell_status.text = status
            
            # Colorer le texte du statut
            for paragraph in cell_status.paragraphs:
                for run in paragraph.runs:
                    if status == "CONFORME":
                        run.font.color.rgb = RGBColor(0, 128, 0)
                    elif status == "PARTIEL":
                        run.font.color.rgb = RGBColor(255, 165, 0)
                    elif status == "NON_CONFORME":
                        run.font.color.rgb = RGBColor(255, 0, 0)
                    run.font.size = Pt(10)
                    run.font.name = 'Arial'
            
            row.cells[5].text = item.get("remarks", "")
            
            # Taille de police pour les autres cellules
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        if run.font.color.rgb is None:  # Si pas déjà coloré
                            run.font.size = Pt(10)
                            run.font.name = 'Arial'
        
        # ---- Taux de conformité ----
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(f"Taux de conformité global : {offer_data.get('total_compliance_rate', 0) * 100:.1f}%")
        run.font.bold = True
        run.font.size = Pt(14)
        run.font.name = 'Arial'
        
        # 3. Sauvegarder le DOCX
        os.makedirs("data/exports", exist_ok=True)
        docx_path = f"data/exports/offre_{session_id}.docx"
        doc.save(docx_path)
        
        # 4. Retourner le fichier
        return FileResponse(
            path=docx_path,
            filename=f"Offre_Technique_{session_id[:8]}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except ImportError:
        logger.error("python-docx non installé")
        raise HTTPException(
            status_code=500,
            detail="python-docx non installé. Installez: pip install python-docx"
        )
    except Exception as e:
        logger.error(f"Erreur d'export: {e}")
        raise HTTPException(status_code=500, detail=str(e))