"""
Classes de base pour les ingestors
"""

import os
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

# ✅ CORRECTION ICI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .schemas import ExtractedDocument, ExtractedChunk, ExtractedMetadata, DocumentType

logger = logging.getLogger(__name__)


class BaseIngestor(ABC):
    """Classe abstraite pour tous les ingestors"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.chunk_size = self.config.get("chunk_size", 800)
        self.chunk_overlap = self.config.get("chunk_overlap", 120)
    
    @abstractmethod
    def can_handle(self, file_path: str, file_type: Optional[str] = None) -> bool:
        """Vérifie si cet ingestor peut traiter le fichier"""
        pass
    
    @abstractmethod
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un document et retourne les données extraites"""
        pass
    
    def _generate_document_id(self, file_path: str) -> str:
        """Génère un ID unique pour le document"""
        return hashlib.md5(file_path.encode()).hexdigest()[:16]
    
    def _chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[ExtractedChunk]:
        """Découpe le texte en chunks avec LangChain"""
        if not text:
            return []
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            
            result.append(ExtractedChunk(
                id=f"{metadata.get('document_id', 'doc')}_chunk_{i}",
                content=chunk,
                metadata=chunk_metadata,
                page_number=metadata.get("page", i // 5)
            ))
        
        return result
    
    def _extract_metadata(self, file_path: str, doc_type: DocumentType) -> ExtractedMetadata:
        """Extrait les métadonnées de base du fichier"""
        stat = os.stat(file_path)
        
        return ExtractedMetadata(
            document_type=doc_type,
            file_size=stat.st_size,
            page_count=None,
            keywords=[],
            custom={
                "file_modified": stat.st_mtime,
                "file_created": stat.st_ctime
            }
        )