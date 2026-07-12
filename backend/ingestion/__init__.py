"""
Module d'ingestion documentaire complet
"""

from .schemas import (
    DocumentType, DocumentStatus, ExtractedMetadata,
    ExtractedChunk, ExtractedDocument, IngestionResult
)
from .document_processor import DocumentProcessor
from .pdf_ingestor import PDFIngestor
from .excel_ingestor import ExcelIngestor
from .image_ingestor import ImageIngestor
from .datasheet_ingestor import DatasheetIngestor
from .standards_ingestor import StandardsIngestor
from .docx_ingestor import DocxIngestor
from .json_ingestor import JsonIngestor

__all__ = [
    "DocumentType",
    "DocumentStatus", 
    "ExtractedMetadata",
    "ExtractedChunk",
    "ExtractedDocument",
    "IngestionResult",
    "DocumentProcessor",
    "PDFIngestor",
    "ExcelIngestor",
    "ImageIngestor",
    "DatasheetIngestor",
    "StandardsIngestor",
    "DocxIngestor",
    "JsonIngestor",
]