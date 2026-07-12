"""
Test de l'OCR
"""

import pytesseract
from PIL import Image
import os

def test_ocr():
    print("🔍 Test de l'OCR...")
    
    # 1. Vérifier Tesseract
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
    except Exception as e:
        print(f"❌ Tesseract non trouvé: {e}")
        print("   Assurez-vous que Tesseract est installé et dans le PATH")
        return False
    
    # 2. Vérifier les langues disponibles
    try:
        langs = pytesseract.get_languages()
        print(f"✅ Langues disponibles: {langs}")
    except:
        pass
    
    # 3. Créer une image de test
    from PIL import Image, ImageDraw, ImageFont
    
    print("\n📸 Création d'une image de test...")
    
    # Créer une image avec du texte
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)
    
    # Texte à tester
    text = "Switch Core VLAN 10"
    d.text((10, 10), text, fill='black')
    d.text((10, 40), "Adresse IP: 192.168.1.1", fill='black')
    
    # Sauvegarder l'image
    test_img = "test_ocr.png"
    img.save(test_img)
    print(f"✅ Image de test créée: {test_img}")
    
    # 4. Tester l'OCR
    print("\n🔍 Test de l'OCR sur l'image...")
    
    try:
        # OCR en français
        result = pytesseract.image_to_string(Image.open(test_img), lang='fra')
        print(f"✅ Résultat OCR (français):")
        print("-" * 40)
        print(result)
        print("-" * 40)
        
        # Nettoyer
        os.remove(test_img)
        return True
        
    except Exception as e:
        print(f"❌ Erreur OCR: {e}")
        return False


def test_with_your_image():
    """Test avec votre propre image"""
    print("\n" + "="*60)
    print("🖼️ TEST OCR AVEC VOTRE IMAGE")
    print("="*60)
    
    image_path = input("\n📁 Entrez le chemin de votre image: ").strip()
    
    if not os.path.exists(image_path):
        print(f"❌ Image non trouvée: {image_path}")
        return
    
    try:
        # OCR en français
        result = pytesseract.image_to_string(
            Image.open(image_path), 
            lang='fra'
        )
        
        print("\n📝 Texte extrait:")
        print("-" * 40)
        if result.strip():
            print(result)
        else:
            print("⚠️ Aucun texte détecté (image trop sombre, texte illisible...)")
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    print("\n🧪 TEST OCR COMPLET")
    print("="*60)
    
    # Test de base
    success = test_ocr()
    
    if success:
        print("\n🎉 L'OCR fonctionne !")
        
        # Proposer de tester une image
        choice = input("\n👉 Tester avec votre image ? (o/n): ").strip().lower()
        if choice == 'o':
            test_with_your_image()
    else:
        print("\n⚠️ L'OCR ne fonctionne pas.")
        print("\n🔧 Solutions:")
        print("1. Installez Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Ajoutez-le au PATH")
        print("3. Redémarrez votre terminal")
        print("4. Vérifiez avec: tesseract --version")