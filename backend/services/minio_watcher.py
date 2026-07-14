# backend/services/minio_watcher.py

import os
import time
import logging
import tempfile
from threading import Thread
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from ingestion import DocumentProcessor
from services.vector_store import VectorStore
from services.document_service import DocumentService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


class MinioWatcher:
    """
    Surveille MinIO pour les nouveaux fichiers
    Détecte automatiquement les nouveaux documents et les indexe
    """
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.seen_files = set()
        self.running = False
        self.thread = None
        
        self.storage = StorageService()
        self.processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.doc_service = DocumentService()
        
        self.prefix = os.getenv("KNOWLEDGE_BASE_PREFIX", "knowledge_base/")
        
    def start(self):
        """Démarre la surveillance"""
        if self.running:
            return
        
        self.running = True
        self.thread = Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info("✅ Surveillance MinIO démarrée (intervalle: {}s)".format(self.check_interval))
    
    def stop(self):
        """Arrête la surveillance"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("⏹️ Surveillance MinIO arrêtée")
    
    def _watch_loop(self):
        """Boucle de surveillance"""
        # Initialiser les fichiers déjà vus
        self._refresh_seen_files()
        
        while self.running:
            try:
                self._check_new_files()
            except Exception as e:
                logger.error(f"Erreur de surveillance: {e}")
            time.sleep(self.check_interval)
    
    def _refresh_seen_files(self):
        """Rafraîchit la liste des fichiers déjà vus"""
        try:
            objects = self.storage.list_files(prefix=self.prefix)
            self.seen_files = set(objects)
            logger.info(f"📄 {len(self.seen_files)} fichiers déjà présents dans MinIO")
        except Exception as e:
            logger.error(f"Erreur de rafraîchissement: {e}")
    
    def _check_new_files(self):
        """Vérifie les nouveaux fichiers"""
        try:
            current_files = set(self.storage.list_files(prefix=self.prefix))
            
            # Nouveaux fichiers = dans current_files mais pas dans seen_files
            new_files = current_files - self.seen_files
            
            for file_path in new_files:
                if not file_path.endswith('/'):
                    self._process_new_file(file_path)
            
            # Mettre à jour la liste des fichiers vus
            self.seen_files = current_files
            
        except Exception as e:
            logger.error(f"Erreur de vérification: {e}")
    
    def _process_new_file(self, object_path: str):
        """Traite un nouveau fichier"""
        logger.info(f"📄 Nouveau fichier détecté: {object_path}")
        
        try:
            # 1. Vérifier si déjà indexé
            existing = self.doc_service.get_document_by_minio_path(object_path)
            if existing:
                logger.info(f"  ⏭️ Document déjà indexé")
                return
            
            # 2. Télécharger depuis MinIO en gardant l'extension
            filename = os.path.basename(object_path)
            
            # ✅ Créer un fichier temporaire avec la bonne extension
            import tempfile
            import uuid
            
            # Extraire l'extension du nom de fichier
            _, ext = os.path.splitext(filename)
            
            # Créer un fichier temporaire avec l'extension
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                temp_path = tmp_file.name
            
            # Télécharger vers ce fichier
            self.storage.download_file(object_path, temp_path)
            
            # 3. Lire le contenu pour le hash
            with open(temp_path, 'rb') as f:
                file_content = f.read()
            
            # 4. Ingérer
            doc = self.processor.process_file(temp_path)
            
            if not doc or doc.status.value == "failed":
                error = doc.error if doc else "Erreur d'ingestion"
                logger.error(f"  ❌ Échec d'ingestion: {error}")
                return
            
            # 5. Indexer dans ChromaDB
            vector_ids = []
            for chunk in doc.chunks:
                try:
                    vector_id = self.vector_store.add_document(
                        content=chunk.content,
                        metadata={
                            "document_id": doc.id,
                            "document_type": doc.document_type.value,
                            "source": "minio_watcher",
                            "minio_path": object_path,
                            "filename": doc.filename,
                            "chunk_index": chunk.metadata.get("chunk_index", 0)
                        },
                        collection="knowledge_base"
                    )
                    vector_ids.append(vector_id)
                except Exception as e:
                    logger.warning(f"  ⚠️ Erreur d'indexation chunk: {e}")
            
            # 6. Sauvegarder dans PostgreSQL
            category = object_path.split('/')[1] if len(object_path.split('/')) > 1 else "other"
            doc_id = self.doc_service.save_document(
                doc=doc,
                file_content=file_content,
                minio_path=object_path,
                category=category
            )
            
            logger.info(f"  ✅ Document indexé: {doc.filename} ({len(doc.chunks)} chunks, {len(vector_ids)} vecteurs)")
            
            # 7. Nettoyer
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"  ❌ Erreur de traitement: {e}")
            import traceback
            logger.error(traceback.format_exc())