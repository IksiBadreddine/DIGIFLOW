"""
Test unitaire du module d'ingestion - Version complète
"""

import os
import sys
import tempfile

# Ajouter le chemin du backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import DocumentProcessor

# Imports pour créer les fichiers de test
from reportlab.pdfgen import canvas
import pandas as pd
from PIL import Image, ImageDraw


def test_pdf():
    """Test PDF"""
    print("\n📄 Test PDF...")
    
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(pdf_path)
    c.drawString(50, 750, "SPECIFICATIONS TECHNIQUES")
    c.drawString(50, 730, "1. Switch 24 ports Gigabit Ethernet")
    c.drawString(50, 710, "2. Support PoE+ IEEE 802.3at")
    c.drawString(50, 690, "3. Alimentation redondante")
    c.save()
    
    try:
        processor = DocumentProcessor()
        result = processor.process_file(pdf_path)
        
        assert result is not None, "Aucun résultat"
        assert len(result.chunks) > 0, "Aucun chunk"
        assert len(result.full_text) > 50, "Texte trop court"
        
        print(f"✅ Type: {result.document_type.value}")
        print(f"✅ Chunks: {len(result.chunks)}")
        print(f"✅ Texte: {len(result.full_text)} caractères")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    finally:
        try:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except:
            pass


def test_excel():
    """Test Excel BOQ"""
    print("\n📊 Test Excel...")
    
    temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    excel_path = temp_excel.name
    temp_excel.close()
    
    data = {
        "Designation": ["Switch 24P", "Fibre 5M"],
        "Reference": ["WS-C2960X", "LC-5M"],
        "Quantite": [2, 10]
    }
    df = pd.DataFrame(data)
    df.to_excel(excel_path, sheet_name="BOQ", index=False)
    
    try:
        processor = DocumentProcessor()
        result = processor.process_file(excel_path)
        
        assert result is not None, "Aucun résultat"
        assert result.document_type.value == "excel_boq", "Mauvais type"
        assert len(result.tables) > 0, "Aucun tableau"
        
        print(f"✅ Type: {result.document_type.value}")
        print(f"✅ Tableaux: {len(result.tables)}")
        print(f"✅ Chunks: {len(result.chunks)}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    finally:
        try:
            if os.path.exists(excel_path):
                os.unlink(excel_path)
        except:
            pass


def test_image():
    """Test Image avec OCR"""
    print("\n🖼️ Test Image...")
    
    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img_path = temp_img.name
    temp_img.close()
    
    img = Image.new('RGB', (400, 150), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Switch Core", fill='black')
    d.text((10, 40), "VLAN 10 - Admin", fill='black')
    img.save(img_path)
    
    try:
        processor = DocumentProcessor()
        result = processor.process_file(img_path)
        
        assert result is not None, "Aucun résultat"
        assert result.document_type.value == "image", "Mauvais type"
        
        print(f"✅ Type: {result.document_type.value}")
        print(f"✅ Texte extrait: {len(result.full_text)} caractères")
        print(f"✅ Images: {len(result.images)}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    finally:
        try:
            if os.path.exists(img_path):
                os.unlink(img_path)
        except:
            pass



def test_datasheet():
    """Test Datasheet fabricant"""
    print("\n📦 Test Datasheet...")
    
    # ✅ Nom de fichier explicite avec "datasheet"
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_pdf.name
    temp_pdf.close()
    
    # Renommer avec "datasheet" dans le nom
    new_path = pdf_path.replace('.pdf', '_datasheet.pdf')
    os.rename(pdf_path, new_path)
    pdf_path = new_path
    
    c = canvas.Canvas(pdf_path)
    c.drawString(50, 750, "CISCO DATASHEET")
    c.drawString(50, 730, "Model: WS-C2960X-24PS-L")
    c.drawString(50, 710, "24 ports Gigabit Ethernet")
    c.drawString(50, 690, "PoE+ IEEE 802.3at")
    c.save()
    
    try:
        processor = DocumentProcessor()
        result = processor.process_file(pdf_path)
        
        assert result is not None, "Aucun résultat"
        print(f"✅ Type détecté: {result.document_type.value}")
        assert result.document_type.value == "pdf_datasheet", f"Mauvais type: {result.document_type.value}"
        
        print(f"✅ Type: {result.document_type.value}")
        print(f"✅ Fabricant: {result.metadata.manufacturer}")
        print(f"✅ Chunks: {len(result.chunks)}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    finally:
        try:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except:
            pass


def test_standard():
    """Test Norme technique"""
    print("\n📏 Test Norme...")
    
    # ✅ Nom de fichier explicite avec "ieee"
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_pdf.name
    temp_pdf.close()
    
    new_path = pdf_path.replace('.pdf', '_ieee.pdf')
    os.rename(pdf_path, new_path)
    pdf_path = new_path
    
    c = canvas.Canvas(pdf_path)
    c.drawString(50, 750, "IEEE 802.3-2022")
    c.drawString(50, 730, "Standard for Ethernet")
    c.drawString(50, 710, "Section 1: Scope")
    c.drawString(50, 690, "Section 2: References")
    c.save()
    
    try:
        processor = DocumentProcessor()
        result = processor.process_file(pdf_path)
        
        assert result is not None, "Aucun résultat"
        print(f"✅ Type détecté: {result.document_type.value}")
        assert result.document_type.value == "standard", f"Mauvais type: {result.document_type.value}"
        
        print(f"✅ Type: {result.document_type.value}")
        print(f"✅ Code: {result.metadata.standard_code}")
        print(f"✅ Sections: {len(result.metadata.custom.get('sections', []))}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    finally:
        try:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except:
            pass


if __name__ == "__main__":
    print("\n" + "="*50)
    print("🧪 TEST UNITAIRE - MODULE INGESTION")
    print("="*50)
    
    tests = [
        ("PDF", test_pdf),
        ("Excel", test_excel),
        ("Image", test_image),
        ("Datasheet", test_datasheet),
        ("Norme", test_standard),
    ]
    
    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))
    
    print("\n" + "="*50)
    print("📊 RÉSULTATS")
    print("="*50)
    
    all_passed = True
    for name, success in results:
        status = "✅ OK" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if not success:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 TOUS LES TESTS SONT PASSÉS !")
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
    print("="*50)