"""
Offer Generation Router
POST /api/generate-offer  — Generate full technical offer from session
GET  /api/export/{session_id} — Export offer as DOCX
"""
import os
import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from services.llm_service import generate_offer
from models.schemas import GeneratedOffer, OfferSection, ComplianceRow, ConformityStatus

router = APIRouter(prefix="/api", tags=["offer"])

# Shared sessions from analyze router (import reference)
from routers.analyze import sessions


class GenerateOfferRequest(BaseModel):
    session_id: str
    selected_product_ids: list[str] = []  # empty = use top-ranked


@router.post("/generate-offer")
def generate_technical_offer(req: GenerateOfferRequest):
    """Generate a complete technical offer for a given session."""
    if req.session_id not in sessions:
        raise HTTPException(404, "Session introuvable ou expirée")

    session = sessions[req.session_id]
    all_products = session["products"]

    # Filter to selected products, or take top 3
    if req.selected_product_ids:
        products = [p for p in all_products if p["product_id"] in req.selected_product_ids]
    else:
        products = sorted(all_products, key=lambda x: x["compliance_score"], reverse=True)[:3]

    if not products:
        raise HTTPException(400, "Aucun produit sélectionné")

    # Compute global compliance rate
    all_rows = []
    for p in products:
        all_rows.extend(p.get("compliance_rows", []))
    if all_rows:
        conformes = sum(1 for r in all_rows if r.get("status") == "CONFORME")
        compliance_rate = conformes / len(all_rows)
    else:
        compliance_rate = 0.0

    # GPT-4 offer generation
    offer_data = generate_offer(
        summary=session["summary"],
        constraints=session["constraints"],
        products=products,
        compliance_rate=compliance_rate,
    )

    # Build compliance table (from best product)
    best = products[0]
    compliance_table = [
        ComplianceRow(
            requirement_id=r.get("requirement_id", ""),
            requirement_text=r.get("requirement_text", ""),
            specified_value=r.get("specified_value"),
            product_response=r.get("product_response", ""),
            status=ConformityStatus(r.get("status", "NON_VERIFIE")),
            remarks=r.get("remarks"),
        )
        for r in best.get("compliance_rows", [])
    ]

    offer = GeneratedOffer(
        title=offer_data.get("title", "Offre Technique"),
        reference=offer_data.get("reference", f"REF-{req.session_id.upper()}"),
        sections=[OfferSection(**s) for s in offer_data.get("sections", [])],
        boq=offer_data.get("boq", []),
        compliance_table=compliance_table,
        total_compliance_rate=compliance_rate,
    )

    # Store offer in session
    sessions[req.session_id]["offer"] = offer.model_dump()

    return offer.model_dump()


@router.get("/export/{session_id}")
def export_offer_docx(session_id: str):
    """Export the generated offer as a DOCX file."""
    if session_id not in sessions:
        raise HTTPException(404, "Session introuvable")
    if "offer" not in sessions[session_id]:
        raise HTTPException(400, "Offre non encore générée pour cette session")

    offer = sessions[session_id]["offer"]
    doc = _build_docx(offer)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    filename = f"Offre_Technique_{session_id}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────
# DOCX builder
# ──────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _build_docx(offer: dict) -> Document:
    doc = Document()

    # Styles
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    # ── Cover page ──
    title_p = doc.add_heading(offer["title"], level=0)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title_p.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    doc.add_paragraph(f"Référence : {offer['reference']}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(
        f"Taux de conformité global : {round(offer['total_compliance_rate'] * 100, 1)} %"
    ).alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()

    # ── Sections ──
    for section in offer["sections"]:
        doc.add_heading(section["title"], level=1)
        for line in section["content"].split("\n"):
            if line.strip():
                doc.add_paragraph(line.strip())

    doc.add_page_break()

    # ── BOQ ──
    doc.add_heading("Bill of Quantities (BOQ)", level=1)
    if offer["boq"]:
        headers = ["Pos.", "Désignation", "Référence", "Fabricant", "Unité", "Qté", "Remarques"]
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"

        hdr_row = table.rows[0]
        for i, h in enumerate(headers):
            cell = hdr_row.cells[i]
            cell.text = h
            _set_cell_bg(cell, "1F3864")
            for run in cell.paragraphs[0].runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        for item in offer["boq"]:
            row = table.add_row()
            values = [
                str(item.get("pos", "")),
                item.get("designation", ""),
                item.get("reference", ""),
                item.get("manufacturer", ""),
                item.get("unit", "U"),
                str(item.get("quantity", "")),
                item.get("remarks", ""),
            ]
            for i, v in enumerate(values):
                row.cells[i].text = v

    doc.add_page_break()

    # ── Compliance table ──
    doc.add_heading("Tableau de Conformité", level=1)
    if offer["compliance_table"]:
        headers = ["ID", "Exigence", "Valeur requise", "Réponse produit", "Statut", "Remarques"]
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"

        hdr_row = table.rows[0]
        for i, h in enumerate(headers):
            cell = hdr_row.cells[i]
            cell.text = h
            _set_cell_bg(cell, "2E75B6")
            for run in cell.paragraphs[0].runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        status_colors = {
            "CONFORME": "E2EFDA",
            "PARTIEL": "FFF2CC",
            "NON_CONFORME": "FCE4D6",
            "NON_VERIFIE": "F2F2F2",
        }

        for r in offer["compliance_table"]:
            row = table.add_row()
            values = [
                r.get("requirement_id", ""),
                r.get("requirement_text", ""),
                r.get("specified_value", "") or "",
                r.get("product_response", ""),
                r.get("status", ""),
                r.get("remarks", "") or "",
            ]
            for i, v in enumerate(values):
                row.cells[i].text = v
            # Color status cell
            status = r.get("status", "NON_VERIFIE")
            _set_cell_bg(row.cells[4], status_colors.get(status, "F2F2F2"))

    return doc
