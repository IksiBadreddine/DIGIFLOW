"""
Ingestor pour Excel BOQ (Bill of Quantities)
"""

import os
import logging
import pandas as pd
from typing import Optional, Dict, Any, List

from .base import BaseIngestor
from .schemas import (
    ExtractedDocument, ExtractedChunk, ExtractedMetadata,
    DocumentType, DocumentStatus
)

logger = logging.getLogger(__name__)


class ExcelIngestor(BaseIngestor):
    """Ingestor pour les fichiers Excel (BOQ)"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.sheet_names = self.config.get("sheet_names", ["BOQ", "BoQ", "boq"])
        self.auto_detect_boq = self.config.get("auto_detect_boq", True)
    
    def can_handle(self, file_path: str, file_type: Optional[str] = None) -> bool:
        """Vérifie si c'est un fichier Excel"""
        ext = file_path.lower()
        return ext.endswith(('.xlsx', '.xls', '.xlsm', '.csv'))
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un fichier Excel BOQ"""
        logger.info(f"Ingestion du BOQ Excel: {file_path}")
        
        metadata = self._extract_metadata(file_path, DocumentType.EXCEL_BOQ)
        
        try:
            # Lire le fichier Excel
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, sheet_name=None)
            
            full_text = ""
            tables = []
            chunks = []
            chunk_id = 0
            
            # Traiter chaque feuille
            for sheet_name, data in df.items():
                if isinstance(data, dict):
                    # Cas Excel multi-feuilles
                    for s_name, s_data in data.items():
                        text, table_data, sheet_chunks = self._process_sheet(
                            s_data, s_name, file_path, chunk_id
                        )
                        full_text += text + "\n"
                        tables.extend(table_data)
                        chunks.extend(sheet_chunks)
                        chunk_id += len(sheet_chunks)
                else:
                    # Cas DataFrame simple
                    text, table_data, sheet_chunks = self._process_sheet(
                        data, sheet_name, file_path, chunk_id
                    )
                    full_text += text + "\n"
                    tables.extend(table_data)
                    chunks.extend(sheet_chunks)
                    chunk_id += len(sheet_chunks)
            
            # Métadonnées BOQ spécifiques
            metadata.custom["sheet_count"] = len(df) if isinstance(df, dict) else 1
            metadata.custom["row_count"] = sum(len(v) for v in df.values()) if isinstance(df, dict) else len(df)
            
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.EXCEL_BOQ,
                metadata=metadata,
                full_text=full_text,
                chunks=chunks,
                tables=tables,
                status=DocumentStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Erreur d'ingestion Excel: {e}")
            return ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=DocumentType.EXCEL_BOQ,
                metadata=metadata,
                full_text="",
                chunks=[],
                status=DocumentStatus.FAILED,
                error=str(e)
            )
    
    def _process_sheet(self, df: pd.DataFrame, sheet_name: str, file_path: str, chunk_id: int) -> tuple:
        """Traite une feuille Excel"""
        # Nettoyer les données
        df = df.dropna(how='all')
        df = df.fillna('')
        
        # Convertir en texte
        text = f"\n=== Feuille: {sheet_name} ===\n"
        text += df.to_string(index=False) + "\n"
        
        # Extraire les tableaux structurés
        table_data = {
            "sheet_name": sheet_name,
            "columns": df.columns.tolist(),
            "rows": df.to_dict('records'),
            "shape": df.shape
        }
        
        # Créer des chunks
        chunks = []
        if len(text) > 500:
            # Diviser par lignes pour les grands tableaux
            for i in range(0, len(df), 20):
                chunk_df = df.iloc[i:i+20]
                chunk_text = f"\n=== Feuille: {sheet_name} (lignes {i+1}-{i+len(chunk_df)}) ===\n"
                chunk_text += chunk_df.to_string(index=False)
                
                chunks.append(ExtractedChunk(
                    id=f"{self._generate_document_id(file_path)}_chunk_{chunk_id + i//20}",
                    content=chunk_text,
                    metadata={
                        "sheet_name": sheet_name,
                        "row_start": i,
                        "row_end": i + len(chunk_df),
                        "document_id": self._generate_document_id(file_path)
                    }
                ))
        else:
            chunks.append(ExtractedChunk(
                id=f"{self._generate_document_id(file_path)}_chunk_{chunk_id}",
                content=text,
                metadata={
                    "sheet_name": sheet_name,
                    "document_id": self._generate_document_id(file_path)
                }
            ))
        
        return text, [table_data], chunks