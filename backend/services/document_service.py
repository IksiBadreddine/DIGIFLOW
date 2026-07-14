# backend/services/document_service.py

import hashlib
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from models.database import SessionLocal, Document, DocumentChunk, DocumentMeta, Session as SessionModel

logger = logging.getLogger(__name__)


class DocumentService:
    """Service de gestion des documents (PostgreSQL)"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def save_document(
        self,
        doc,
        file_content: bytes,
        minio_path: str,
        category: str = "knowledge_base",
        session_id: str = None
    ) -> str:
        """
        Sauvegarde un document dans PostgreSQL
        """
        # 1. Calculer le hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 2. Vérifier si le document existe déjà
        existing = self.db.query(Document).filter(
            Document.file_hash == file_hash
        ).first()
        
        if existing:
            logger.info(f"Document déjà existant: {existing.id}")
            return existing.id
        
        # 3. Créer le document
        doc_id = str(uuid.uuid4())
        document = Document(
            id=doc_id,
            filename=doc.filename,
            file_path=minio_path,
            file_hash=file_hash,
            file_size=doc.metadata.file_size,
            mime_type=self._get_mime_type(doc.filename),
            document_type=doc.document_type.value,
            category=category,
            status=doc.status.value,
            title=doc.metadata.title,
            author=doc.metadata.author,
            page_count=doc.metadata.page_count,
            manufacturer=doc.metadata.manufacturer,
            standard_code=doc.metadata.standard_code,
            full_text=doc.full_text[:100000],
            chunk_count=len(doc.chunks),
            word_count=len(doc.full_text.split()),
            session_id=session_id,
            tags=doc.metadata.keywords,
            processed_at=doc.processed_at
        )
        
        self.db.add(document)
        self.db.commit()
        
        # 4. Sauvegarder les chunks
        for chunk in doc.chunks:
            chunk_model = DocumentChunk(
                id=chunk.id,
                document_id=doc_id,
                chunk_index=chunk.metadata.get("chunk_index", 0),
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.metadata.get("section_title"),
                chunk_metadata=chunk.metadata,
                vector_id=chunk.id
            )
            self.db.add(chunk_model)
        
        self.db.commit()
        
        # 5. Sauvegarder les métadonnées
        for key, value in doc.metadata.custom.items():
            meta = DocumentMeta(
                id=str(uuid.uuid4()),  # ✅ Ajouter un ID généré
                document_id=doc_id,
                key=key,
                value=str(value) if not isinstance(value, dict) else None,
                value_type="string",
                json_value=value if isinstance(value, dict) else None
            )
            self.db.add(meta)
        
        self.db.commit()
        
        logger.info(f"✅ Document sauvegardé: {doc_id}")
        return doc_id
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Récupère un document par son ID"""
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def get_document_by_hash(self, file_hash: str) -> Optional[Document]:
        """Récupère un document par son hash"""
        return self.db.query(Document).filter(Document.file_hash == file_hash).first()
    
    def get_document_by_minio_path(self, minio_path: str) -> Optional[Document]:
        """Récupère un document par son chemin MinIO"""
        return self.db.query(Document).filter(Document.file_path == minio_path).first()
    
    def get_documents_by_category(self, category: str) -> List[Document]:
        """Récupère tous les documents d'une catégorie"""
        return self.db.query(Document).filter(Document.category == category).all()
    
    def search_documents(self, query: str, category: str = None, limit: int = 10) -> List[Document]:
        """Recherche des documents"""
        filters = []
        if category:
            filters.append(Document.category == category)
        
        return self.db.query(Document).filter(
            Document.full_text.ilike(f"%{query}%"),
            *filters
        ).limit(limit).all()
    
    def update_document_status(self, document_id: str, status: str):
        """Met à jour le statut d'un document"""
        document = self.get_document(document_id)
        if document:
            document.status = status
            document.updated_at = datetime.now()
            self.db.commit()
    
    def delete_document(self, document_id: str):
        """Supprime un document"""
        document = self.get_document(document_id)
        if document:
            self.db.delete(document)
            self.db.commit()
            logger.info(f"✅ Document supprimé: {document_id}")
    
    def close(self):
        """Ferme la connexion"""
        self.db.close()
    
    def _get_mime_type(self, filename: str) -> str:
        """Détecte le MIME type"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'txt': 'text/plain',
            'json': 'application/json'
        }
        return mime_types.get(ext, 'application/octet-stream')