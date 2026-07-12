"""
Pipeline principal d'ingestion documentaire - Version complète
"""

import os
import logging
from typing import List, Dict, Any, Optional

from .schemas import ExtractedDocument, IngestionResult, DocumentStatus
from .datasheet_ingestor import DatasheetIngestor
from .standards_ingestor import StandardsIngestor
from .pdf_ingestor import PDFIngestor
from .excel_ingestor import ExcelIngestor
from .image_ingestor import ImageIngestor

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Orchestrateur du pipeline d'ingestion complet"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.vector_indexer = self.config.get("vector_indexer")
        
        # ✅ ORDRE CORRECT : Les plus spécifiques d'abord
        self.ingestors = [
            DatasheetIngestor(),   # 1. D'abord les datasheets (le plus spécifique)
            StandardsIngestor(),    # 2. Ensuite les normes
            ImageIngestor(),        # 3. Images
            ExcelIngestor(),        # 4. Excel
            PDFIngestor(),          # 5. PDF standards (le plus général, EN DERNIER)
        ]
    
    def process_file(self, file_path: str) -> Optional[ExtractedDocument]:
        """Traite un fichier avec l'ingestor approprié"""
        if not os.path.exists(file_path):
            logger.error(f"Fichier inexistant: {file_path}")
            return None
        
        logger.info(f"Traitement du fichier: {file_path}")
        
        # Trouver l'ingestor approprié
        for ingestor in self.ingestors:
            if ingestor.can_handle(file_path):
                try:
                    result = ingestor.ingest(file_path)
                    if result and result.status != DocumentStatus.FAILED:
                        return result
                except Exception as e:
                    logger.error(f"Erreur avec {ingestor.__class__.__name__}: {e}")
                    continue
        
        logger.error(f"Aucun ingestor pour: {file_path}")
        return None
    
    def process_and_index(self, file_path: str) -> IngestionResult:
        """Traite et indexe un document dans la base vectorielle"""
        doc = self.process_file(file_path)
        
        if not doc or doc.status == DocumentStatus.FAILED:
            return IngestionResult(
                document_id=doc.id if doc else None,
                chunks_indexed=0,
                vector_ids=[],
                metadata={},
                success=False,
                error=doc.error if doc else "Document non traité"
            )
        
        # Indexation vectorielle
        vector_ids = []
        if self.vector_indexer:
            try:
                for chunk in doc.chunks:
                    vector_id = self.vector_indexer.add_document(
                        content=chunk.content,
                        metadata={
                            **chunk.metadata,
                            "document_id": doc.id,
                            "document_type": doc.document_type.value,
                            "filename": doc.filename
                        }
                    )
                    vector_ids.append(vector_id)
                
                logger.info(f"Indexé {len(vector_ids)} chunks pour {doc.filename}")
            except Exception as e:
                logger.error(f"Erreur d'indexation: {e}")
                return IngestionResult(
                    document_id=doc.id,
                    chunks_indexed=len(doc.chunks),
                    vector_ids=[],
                    metadata=doc.metadata.dict(),
                    success=False,
                    error=str(e)
                )
        
        return IngestionResult(
            document_id=doc.id,
            chunks_indexed=len(doc.chunks),
            vector_ids=vector_ids,
            metadata=doc.metadata.dict(),
            success=True
        )
    
    def process_folder(self, folder_path: str) -> List[ExtractedDocument]:
        """Traite tous les fichiers d'un dossier"""
        results = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                doc = self.process_file(file_path)
                if doc:
                    results.append(doc)
        
        return results