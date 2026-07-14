# backend/scripts/index_from_minio.py

"""
Indexe tous les documents depuis MinIO
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import DocumentProcessor
from services.storage_service import StorageService
from services.vector_store import VectorStore
from services.document_service import DocumentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def index_from_minio():
    """
    Indexe tous les documents depuis MinIO
    """
    logger.info("📚 Indexation depuis MinIO...")
    
    # 1. Initialiser les services
    storage = StorageService()
    processor = DocumentProcessor()
    vector_store = VectorStore()
    doc_service = DocumentService()
    
    # 2. Lister les fichiers dans MinIO
    prefix = os.getenv("KNOWLEDGE_BASE_PREFIX", "knowledge_base/")
    objects = storage.list_files(prefix=prefix)
    
    if not objects:
        logger.warning("⚠️ Aucun fichier trouvé dans MinIO")
        return 0
    
    logger.info(f"📄 {len(objects)} fichiers trouvés")
    
    # 3. Traiter chaque fichier
    total_docs = 0
    
    for object_path in objects:
        # Ignorer les dossiers (qui se terminent par /)
        if object_path.endswith('/'):
            continue
        
        logger.info(f"📄 {object_path}")
        
        try:
            # Télécharger temporairement
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                storage.download_file(object_path, tmp_file.name)
                temp_path = tmp_file.name
            
            # Ingérer le document
            doc = processor.process_file(temp_path)
            
            if doc and doc.status.value == "completed":
                # Indexer dans ChromaDB
                for chunk in doc.chunks:
                    vector_store.add_document(
                        content=chunk.content,
                        metadata={
                            "document_id": doc.id,
                            "document_type": doc.document_type.value,
                            "source": "minio",
                            "minio_path": object_path,
                            "filename": doc.filename,
                            "chunk_index": chunk.metadata.get("chunk_index", 0)
                        },
                        collection="knowledge_base"
                    )
                
                # Sauvegarder dans PostgreSQL
                with open(temp_path, 'rb') as f:
                    file_content = f.read()
                    category = object_path.split('/')[1] if len(object_path.split('/')) > 1 else "other"
                    doc_service.save_document(
                        doc=doc,
                        file_content=file_content,
                        minio_path=object_path,
                        category=category
                    )
                
                total_docs += 1
                logger.info(f"  ✅ Indexé: {doc.filename} ({len(doc.chunks)} chunks)")
            else:
                error = doc.error if doc else "Erreur inconnue"
                logger.warning(f"  ⚠️ Échec: {error}")
            
            # Nettoyer
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"  ❌ Erreur: {e}")
    
    logger.info(f"✅ Total indexé: {total_docs} documents")
    return total_docs


if __name__ == "__main__":
    index_from_minio()