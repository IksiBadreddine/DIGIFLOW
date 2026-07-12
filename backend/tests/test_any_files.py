"""
Test avec n'importe quels fichiers
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import DocumentProcessor


def test_files():
    """Test avec des fichiers choisis par l'utilisateur"""
    
    print("\n" + "="*60)
    print("🧪 TEST AVEC N'IMPORTE QUELS DOCUMENTS")
    print("="*60)
    
    # 1. Demander le chemin du dossier
    folder_path = input("\n📁 Entrez le chemin du dossier contenant vos fichiers: ").strip()
    
    if not os.path.exists(folder_path):
        print(f"❌ Dossier non trouvé: {folder_path}")
        return
    
    # 2. Lister les fichiers
    folder = Path(folder_path)
    files = [f for f in folder.iterdir() if f.is_file()]
    
    if not files:
        print("❌ Aucun fichier trouvé dans ce dossier")
        return
    
    print(f"\n📄 Fichiers trouvés: {len(files)}")
    for f in files[:10]:
        print(f"  - {f.name} ({f.suffix})")
    if len(files) > 10:
        print(f"  ... et {len(files) - 10} autres")
    
    # 3. Demander confirmation
    confirm = input("\n👉 Traiter ces fichiers ? (o/n): ").strip().lower()
    if confirm != 'o':
        print("❌ Annulé")
        return
    
    # 4. Traiter les fichiers
    print("\n" + "="*60)
    print("🔄 TRAITEMENT EN COURS...")
    print("="*60)
    
    processor = DocumentProcessor()
    results = []
    
    for file_path in files:
        try:
            print(f"\n📄 {file_path.name}")
            
            # Ignorer les fichiers trop gros (> 50MB)
            if file_path.stat().st_size > 50 * 1024 * 1024:
                print(f"  ⚠️ Fichier trop gros ({file_path.stat().st_size / 1024 / 1024:.1f} MB) - Ignoré")
                continue
            
            # Traiter le fichier
            doc = processor.process_file(str(file_path))
            
            if doc and doc.status.value == "completed":
                print(f"  ✅ Type: {doc.document_type.value}")
                print(f"  ✅ Chunks: {len(doc.chunks)}")
                print(f"  ✅ Texte: {len(doc.full_text)} caractères")
                
                # Afficher le début du texte si pas trop long
                if doc.full_text:
                    preview = doc.full_text[:100].replace('\n', ' ')
                    print(f"  📝 Extrait: {preview}...")
                
                results.append({
                    "file": file_path.name,
                    "type": doc.document_type.value,
                    "chunks": len(doc.chunks),
                    "success": True
                })
                
            else:
                error = doc.error if doc else "Erreur inconnue"
                print(f"  ❌ Échec: {error}")
                results.append({
                    "file": file_path.name,
                    "type": "error",
                    "success": False,
                    "error": error
                })
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({
                "file": file_path.name,
                "type": "error",
                "success": False,
                "error": str(e)
            })
    
    # 5. Afficher le résumé
    print("\n" + "="*60)
    print("📊 RÉSULTATS")
    print("="*60)
    
    success_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    
    # Grouper par type
    types = {}
    for r in results:
        if r.get("success"):
            doc_type = r.get("type", "unknown")
            types[doc_type] = types.get(doc_type, 0) + 1
    
    print(f"\n📈 {success_count}/{total_count} fichiers traités avec succès")
    
    if types:
        print("\n📊 Types détectés:")
        for doc_type, count in types.items():
            print(f"  - {doc_type}: {count} fichiers")
    
    # Afficher les détails
    print("\n📋 Détails des fichiers traités:")
    for r in results:
        status = "✅" if r.get("success") else "❌"
        doc_type = r.get("type", "error")
        print(f"  {status} {r['file']} → {doc_type}")
    
    return results


def test_single_file():
    """Test avec un seul fichier"""
    
    print("\n" + "="*60)
    print("📄 TEST D'UN SEUL FICHIER")
    print("="*60)
    
    # Demander le chemin du fichier
    file_path = input("\n📁 Entrez le chemin du fichier à tester: ").strip()
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    # Vérifier la taille
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        print(f"⚠️ Fichier trop gros ({file_size / 1024 / 1024:.1f} MB)")
        confirm = input("Continuer quand même ? (o/n): ").strip().lower()
        if confirm != 'o':
            return
    
    print(f"\n📄 Traitement: {os.path.basename(file_path)}")
    print(f"📦 Taille: {file_size / 1024:.1f} KB")
    
    # Créer le processeur
    processor = DocumentProcessor()
    
    try:
        # Traiter le fichier
        doc = processor.process_file(file_path)
        
        if doc and doc.status.value == "completed":
            print("\n✅ DOCUMENT TRAITÉ AVEC SUCCÈS !")
            print("-" * 40)
            print(f"📌 Type détecté: {doc.document_type.value}")
            print(f"📌 Chunks créés: {len(doc.chunks)}")
            print(f"📌 Taille du texte: {len(doc.full_text)} caractères")
            
            # Afficher les métadonnées
            print(f"\n📊 Métadonnées:")
            print(f"  - Nom: {doc.filename}")
            print(f"  - Type: {doc.document_type.value}")
            if doc.metadata.title:
                print(f"  - Titre: {doc.metadata.title}")
            if doc.metadata.author:
                print(f"  - Auteur: {doc.metadata.author}")
            if doc.metadata.page_count:
                print(f"  - Pages: {doc.metadata.page_count}")
            
            # Afficher le début du texte
            if doc.full_text:
                print(f"\n📝 Extrait du texte (300 premiers caractères):")
                print("-" * 40)
                print(doc.full_text[:300] + ("..." if len(doc.full_text) > 300 else ""))
            
            # Afficher les chunks
            if doc.chunks:
                print(f"\n📑 Aperçu des chunks ({len(doc.chunks)} au total):")
                for i, chunk in enumerate(doc.chunks[:3]):
                    print(f"\n  Chunk {i+1} ({len(chunk.content)} caractères):")
                    print(f"  {chunk.content[:150]}...")
            
        else:
            error = doc.error if doc else "Erreur inconnue"
            print(f"\n❌ Échec: {error}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🧪 TEST AVEC N'IMPORTE QUELS DOCUMENTS")
    print("="*60)
    print("\n1. Tester un dossier (tous les fichiers)")
    print("2. Tester un seul fichier")
    
    choice = input("\n👉 Votre choix (1 ou 2): ").strip()
    
    if choice == "2":
        test_single_file()
    else:
        test_files()