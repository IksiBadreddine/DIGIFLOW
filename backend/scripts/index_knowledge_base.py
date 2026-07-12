"""
Script pour indexer la base de connaissances dans ChromaDB
Version simple - sans MinIO ni PostgreSQL
"""

import os
import sys
import logging
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def index_knowledge_base():
    """Indexe tous les documents du dossier knowledge_base"""
    
    logger.info("📚 Indexation de la base de connaissances...")
    
    # Chemin de la base de connaissances
    kb_path = Path("data/knowledge_base")
    
    if not kb_path.exists():
        logger.error(f"❌ Dossier non trouvé: {kb_path}")
        logger.info("   Créez les dossiers:")
        logger.info(f"   {kb_path}/documents_techniques/")
        logger.info(f"   {kb_path}/fiches_produits/")
        logger.info(f"   {kb_path}/normes/")
        return 0
    
    # Initialiser le processeur
    processor = DocumentProcessor()
    
    # Indexer tous les dossiers
    total_docs = 0
    
    for folder in kb_path.iterdir():
        if not folder.is_dir():
            continue
        
        logger.info(f"📁 Traitement: {folder.name}")
        
        # Compter les fichiers
        files = list(folder.glob("*"))
        if not files:
            logger.info(f"   ⚠️ Aucun fichier")
            continue
        
        logger.info(f"   📄 {len(files)} fichiers trouvés")
        
        for file_path in files:
            if not file_path.is_file():
                continue
            
            try:
                logger.info(f"   📄 {file_path.name}")
                
                # Traiter le fichier
                doc = processor.process_file(str(file_path))
                
                if doc and doc.status.value == "completed":
                    logger.info(f"      ✅ Type: {doc.document_type.value}")
                    logger.info(f"      ✅ Chunks: {len(doc.chunks)}")
                    total_docs += 1
                else:
                    error = doc.error if doc else "Inconnu"
                    logger.warning(f"      ⚠️ Échec: {error}")
                    
            except Exception as e:
                logger.error(f"      ❌ Erreur: {e}")
        
        logger.info("")
    
    logger.info(f"✅ Total indexé: {total_docs} documents")
    return total_docs


if __name__ == "__main__":
    index_knowledge_base()