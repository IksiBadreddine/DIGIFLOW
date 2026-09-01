"""
Ingestor pour PDF - Version corrigée
"""

import os
import logging
from typing import Optional, Dict, Any

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class PDFIngestor(BaseIngestor):
    """Ingestor pour les PDF standards"""
    
    def can_handle(self, file_path: str, original_filename: str = None) -> bool:
        """Vérifie si c'est un PDF standard (non datasheet, non norme)"""
        if not file_path.lower().endswith('.pdf'):
            return False
        
        filename = original_filename or os.path.basename(file_path)
        filename = filename.lower()
        
        # ✅ EXCLURE les datasheets (ils ont leur propre ingestor)
        datasheet_keywords = ['datasheet', 'data sheet']
        if any(kw in filename for kw in datasheet_keywords):
            return False
        
        # ✅ EXCLURE les normes (ils ont leur propre ingestor)
        standard_keywords = ['ieee', 'iso', 'tia', 'nf', 'oncf', 'standard', 'norme']
        if any(kw in filename for kw in standard_keywords):
            return False
        
        # ✅ Si le contenu contient des mots-clés de datasheet ou norme, exclure
        try:
            with open(file_path, 'rb') as f:
                content = f.read(500).decode('utf-8', errors='ignore')
                content_upper = content.upper()
                
                if 'DATASHEET' in content_upper or 'MODEL:' in content_upper:
                    return False
                
                if 'IEEE' in content_upper or 'STANDARD' in content_upper:
                    return False
        except:
            pass
        
        return True
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un PDF standard"""
        logger.info(f"Ingestion du PDF: {file_path}")
        
        doc_type = self._detect_document_type(file_path)
        metadata = self._extract_metadata(file_path, doc_type)
        
        try:
            # Essayer avec PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text() or ""
                    full_text += text + "\n"
                
                metadata.page_count = len(reader.pages)
                
            except ImportError:
                # Fallback: lecture brute
                with open(file_path, 'rb') as f:
                    content = f.read()
                    full_text = content.decode('utf-8', errors='ignore')
            
            if not full_text.strip():
                full_text = f"[Document PDF: {os.path.basename(file_path)}]"
            
            # Chunking
            chunks = self._chunk_text(full_text, {
                "document_id": self._generate_document_id(file_path),
                "document_type": doc_type.value,
                "filename": os.path.basename(file_path)
            })
            
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=doc_type,
                metadata=metadata,
                full_text=full_text,
                chunks=chunks,
                status=DocumentStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Erreur d'ingestion PDF: {e}")
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=doc_type,
                metadata=metadata,
                full_text="",
                chunks=[],
                status=DocumentStatus.FAILED,
                error=str(e)
            )
    
    def _detect_document_type(self, file_path: str) -> DocumentType:
        """Détecte le type de document PDF"""
        filename = os.path.basename(file_path).lower()
        
        if "rfp" in filename or "ao" in filename:
            return DocumentType.PDF_RFP
        elif "doe" in filename:
            return DocumentType.PDF_DOE
        else:
            return DocumentType.PDF_SPEC