# backend/test_docx.py

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def test_docx_generation():
    doc = Document()
    
    # Titre
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("TEST DOCX")
    run.font.size = Pt(28)
    run.font.bold = True
    
    # Contenu
    doc.add_paragraph("Ceci est un test de génération DOCX.")
    
    # Sauvegarder
    doc.save("test_output.docx")
    print("✅ DOCX généré avec succès !")

if __name__ == "__main__":
    test_docx_generation()