"""
Schémas pour le module d'ingestion documentaire
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    """Types de documents supportés"""
    PDF_SPEC = "pdf_specification"      # Spécifications techniques
    PDF_RFP = "pdf_rfp"                 # Appel d'offres
    PDF_DOE = "pdf_doe"                 # DOE
    PDF_DATASHEET = "pdf_datasheet"     # Datasheet fabricant
    EXCEL_BOQ = "excel_boq"             # BOQ Excel
    IMAGE = "image"                     # Image/schéma
    STANDARD = "standard"               # Norme technique
    OTHER = "other"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractedMetadata(BaseModel):
    """Métadonnées extraites du document"""
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    version: Optional[str] = None
    document_type: DocumentType
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    language: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    manufacturer: Optional[str] = None  # Pour les datasheets
    standard_code: Optional[str] = None  # Pour les normes
    project: Optional[str] = None
    custom: Dict[str, Any] = Field(default_factory=dict)


class ExtractedChunk(BaseModel):
    """Chunk de texte avec métadonnées"""
    id: str
    content: str
    metadata: Dict[str, Any]
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    table_data: Optional[Dict] = None  # Pour les tableaux
    image_data: Optional[str] = None   # Base64 pour les images


class ExtractedDocument(BaseModel):
    """Document extrait complet"""
    id: str
    filename: str
    file_path: str
    document_type: DocumentType
    metadata: ExtractedMetadata
    full_text: str
    chunks: List[ExtractedChunk]
    tables: List[Dict] = Field(default_factory=list)  # Tableaux extraits
    images: List[str] = Field(default_factory=list)   # Images extraites (base64)
    status: DocumentStatus = DocumentStatus.COMPLETED
    error: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.now)


class IngestionResult(BaseModel):
    """Résultat de l'ingestion"""
    document_id: str
    chunks_indexed: int
    vector_ids: List[str]
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None