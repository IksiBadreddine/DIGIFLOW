"""
Ingestor pour les fichiers JSON
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class JsonIngestor(BaseIngestor):
    """Ingestor pour les fichiers JSON"""
    
    def can_handle(self, file_path: str) -> bool:
        """Vérifie si c'est un fichier JSON"""
        return file_path.lower().endswith('.json')
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un fichier JSON"""
        logger.info(f"Ingestion du JSON: {file_path}")
        
        metadata = self._extract_metadata(file_path, DocumentType.OTHER)
        metadata.custom["file_format"] = "json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convertir en texte lisible
            full_text = self._json_to_text(data)
            
            # Détecter le type de JSON
            doc_type = self._detect_document_type(data, file_path)
            
            # Métadonnées
            metadata.custom["json_keys"] = list(data.keys()) if isinstance(data, dict) else []
            metadata.custom["json_type"] = "dict" if isinstance(data, dict) else "list"
            metadata.custom["json_length"] = len(data) if isinstance(data, (dict, list)) else 0
            
            # Extraire les mots-clés
            metadata.keywords = self._extract_keywords(data)
            
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
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.OTHER,
                metadata=metadata,
                full_text="",
                chunks=[],
                status=DocumentStatus.FAILED,
                error=f"JSON invalide: {e}"
            )
        except Exception as e:
            logger.error(f"Erreur d'ingestion JSON: {e}")
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
    
    def _json_to_text(self, data: Any, prefix: str = "") -> str:
        """Convertit un JSON en texte lisible"""
        if isinstance(data, dict):
            text = ""
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    text += f"{prefix}{key}:\n"
                    text += self._json_to_text(value, prefix + "  ")
                else:
                    text += f"{prefix}{key}: {value}\n"
            return text
        
        elif isinstance(data, list):
            text = ""
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    text += f"{prefix}Élément {i+1}:\n"
                    text += self._json_to_text(item, prefix + "  ")
                else:
                    text += f"{prefix}{i+1}: {item}\n"
            return text
        
        else:
            return f"{prefix}{data}\n"
    
    def _detect_document_type(self, data: Any, file_path: str) -> DocumentType:
        """Détecte le type de document JSON"""
        filename = os.path.basename(file_path).lower()
        
        if "analyse" in filename or "nlp" in filename:
            return DocumentType.OTHER
        if "produits" in filename or "recommandes" in filename:
            return DocumentType.OTHER
        if "compliance" in filename:
            return DocumentType.OTHER
        
        return DocumentType.OTHER
    
    def _extract_keywords(self, data: Any) -> list:
        """Extrait les mots-clés du JSON"""
        keywords = set()
        
        if isinstance(data, dict):
            # Ajouter les clés
            keywords.update(data.keys())
            
            # Parcourir les valeurs
            for value in data.values():
                if isinstance(value, str):
                    # Ajouter les mots importants
                    words = value.split()
                    for word in words:
                        if len(word) > 5 and word.isalpha():
                            keywords.add(word)
        
        elif isinstance(data, list) and data:
            for item in data[:10]:  # Limiter
                if isinstance(item, dict):
                    keywords.update(item.keys())
        
        return list(keywords)