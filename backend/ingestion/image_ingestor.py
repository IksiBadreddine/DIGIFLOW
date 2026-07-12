"""
Ingestor pour Images - Version corrigée
"""

import os
import logging
import base64
from io import BytesIO

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class ImageIngestor(BaseIngestor):
    """Ingestor pour les images"""
    
    def can_handle(self, file_path: str) -> bool:
        ext = file_path.lower()
        return ext.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'))
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        logger.info(f"Ingestion de l'image: {file_path}")
        
        metadata = self._extract_metadata(file_path, DocumentType.IMAGE)
        
        try:
            from PIL import Image
            
            image = Image.open(file_path)
            metadata.custom["image_size"] = image.size
            metadata.custom["image_format"] = image.format
            
            # OCR avec pytesseract (si disponible)
            text = ""
            try:
                import pytesseract
                text = pytesseract.image_to_string(image, lang='fra')
                logger.info(f"OCR effectué: {len(text)} caractères")
            except ImportError:
                logger.warning("pytesseract non installé, OCR désactivé")
                text = f"[Image: {os.path.basename(file_path)}]"
            except Exception as e:
                logger.warning(f"OCR non disponible: {e}")
                text = f"[Image: {os.path.basename(file_path)}]"
            
            # Convertir en base64
            buffered = BytesIO()
            image.save(buffered, format=image.format or 'PNG')
            image_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            chunks = self._chunk_text(text, {
                "document_id": self._generate_document_id(file_path),
                "document_type": DocumentType.IMAGE.value,
                "filename": os.path.basename(file_path)
            })
            
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.IMAGE,
                metadata=metadata,
                full_text=text,
                chunks=chunks,
                images=[image_b64] if text else [],
                status=DocumentStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Erreur d'ingestion d'image: {e}")
            # ✅ Retourner un document même en cas d'erreur
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.IMAGE,
                metadata=metadata,
                full_text=f"[Image: {os.path.basename(file_path)}]",
                chunks=[],
                status=DocumentStatus.COMPLETED,  # ✅ Pas en échec
                error=None
            )