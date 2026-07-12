"""
Ingestor pour les fichiers DOCX (Microsoft Word)
"""

import os
import logging
from typing import Optional, Dict, Any

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class DocxIngestor(BaseIngestor):
    """Ingestor pour les fichiers DOCX"""
    
    def can_handle(self, file_path: str) -> bool:
        """Vérifie si c'est un fichier DOCX"""
        return file_path.lower().endswith('.docx')
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un fichier DOCX"""
        logger.info(f"Ingestion du DOCX: {file_path}")
        
        doc_type = DocumentType.OTHER
        metadata = self._extract_metadata(file_path, doc_type)
        metadata.custom["file_format"] = "docx"
        
        try:
            # Utiliser python-docx pour extraire le texte
            from docx import Document
            
            doc = Document(file_path)
            
            # Extraire le texte de tous les paragraphes
            full_text = ""
            for para in doc.paragraphs:
                full_text += para.text + "\n"
            
            # Extraire le texte des tableaux
            for table in doc.tables:
                for row in table.rows:
                    row_text = ""
                    for cell in row.cells:
                        row_text += cell.text + " "
                    full_text += row_text + "\n"
            
            # Détecter si c'est une offre technique
            doc_type = self._detect_document_type(full_text, file_path)
            
            # Métadonnées
            if doc.core_properties.title:
                metadata.title = doc.core_properties.title
            if doc.core_properties.author:
                metadata.author = doc.core_properties.author
            if doc.core_properties.created:
                metadata.date = str(doc.core_properties.created)
            
            metadata.custom["paragraphs"] = len(doc.paragraphs)
            metadata.custom["tables"] = len(doc.tables)
            
            # Chunking
            chunks = self._chunk_text(full_text, {
                "document_id": self._generate_document_id(file_path),
                "document_type": doc_type.value,
                "filename": os.path.basename(file_path)
            })
            
            # Extraire les mots-clés
            metadata.keywords = self._extract_keywords(full_text)
            
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
            
        except ImportError:
            logger.error("python-docx non installé")
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.OTHER,
                metadata=metadata,
                full_text="",
                chunks=[],
                status=DocumentStatus.FAILED,
                error="python-docx non installé. Installez: pip install python-docx"
            )
        except Exception as e:
            logger.error(f"Erreur d'ingestion DOCX: {e}")
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.OTHER,
                metadata=metadata,
                full_text="",
                chunks=[],
                status=DocumentStatus.FAILED,
                error=str(e)
            )
    
    def _detect_document_type(self, text: str, file_path: str) -> DocumentType:
        """Détecte le type de document"""
        filename = os.path.basename(file_path).lower()
        text_lower = text.lower()
        
        # Détection par nom
        if "offre" in filename or "offer" in filename:
            return DocumentType.OTHER  # On pourrait ajouter un type OFFRES
        
        # Détection par contenu
        keywords = {
            "offre": ["offre", "proposition", "devis", "prix"],
            "rapport": ["rapport", "analyse", "conclusion"],
            "technique": ["technique", "spécification", "configuration"]
        }
        
        for doc_type, words in keywords.items():
            if any(word in text_lower for word in words):
                return DocumentType.OTHER
        
        return DocumentType.OTHER
    
    def _extract_keywords(self, text: str) -> list:
        """Extrait les mots-clés du DOCX"""
        keywords = set()
        
        # Mots-clés courants dans les offres
        common_keywords = [
            "Offre", "Proposition", "Devis", "Prix", "Total",
            "Solution", "Technique", "Configuration", "Équipement",
            "Switch", "Routeur", "Caméra", "Onduleur", "Serveur"
        ]
        
        for kw in common_keywords:
            if kw.lower() in text.lower():
                keywords.add(kw)
        
        return list(keywords)