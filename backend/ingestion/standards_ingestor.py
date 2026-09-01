"""
Ingestor pour normes et standards techniques
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class StandardsIngestor(BaseIngestor):
    """Ingestor spécialisé pour les normes techniques"""
    
    STANDARD_PATTERNS = {
        "IEEE": r"IEEE\s*(\d{3,4}(?:\.\d+)?[a-z]*)",
        "ISO": r"ISO\s*(\d{3,5}(?:-\d+)?)(?::\s*(\d{4}))?",
        "TIA": r"TIA[/-]?(\d{3,4})",
        "NF": r"NF\s*([A-Z]{2,3}\s*\d{3,4})",
        "ONCF": r"ONCF\s*([A-Z]{2,3}\s*\d{3,4})",
        "CENELEC": r"CENELEC\s*([A-Z]{2,3}\s*\d{3,4})",
        "ITU": r"ITU-T?\s*([A-Z]\.\d{3,4})",
        "ETSI": r"ETSI\s*([A-Z]{2,3}\s*\d{3,4})",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.extract_cross_references = self.config.get("extract_cross_references", True)
        self.detect_sections = self.config.get("detect_sections", True)
    
    def can_handle(self, file_path: str, original_filename: str = None) -> bool:
        """Détecte si c'est un document de norme"""
        if not file_path.lower().endswith('.pdf'):
            return False
        
        filename = original_filename or os.path.basename(file_path)
        filename = filename.lower()
        
        # 1. Détection par nom de fichier
        standard_keywords = ['ieee', 'iso', 'tia', 'nf', 'oncf', 'standard', 'norme']
        if any(kw in filename for kw in standard_keywords):
            return True
        
        # 2. Détection par contenu
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1000).decode('utf-8', errors='ignore')
                content_upper = content.upper()
                
                # Vérifier les patterns de normes
                import re
                patterns = [
                    r'IEEE\s*\d{3,4}',
                    r'ISO\s*\d{3,5}',
                    r'TIA[/-]?\d{3,4}',
                ]
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        return True
                
                standard_keywords = ['STANDARD', 'NORM', 'INTERNATIONAL STANDARD']
                if any(kw in content_upper for kw in standard_keywords):
                    return True
        except:
            pass
        
        return False
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère une norme"""
        logger.info(f"Ingestion de la norme: {file_path}")
        
        doc_type = DocumentType.STANDARD
        metadata = self._extract_metadata(file_path, doc_type)
        
        try:
            full_text = self._extract_text(file_path)
            
            standard_info = self._extract_standard_info(full_text, file_path)
            
            metadata.standard_code = standard_info.get("code")
            metadata.title = standard_info.get("title")
            metadata.version = standard_info.get("version")
            metadata.date = standard_info.get("date")
            
            metadata.custom.update({
                "standard_type": standard_info.get("type"),
                "standard_organization": standard_info.get("organization"),
                "sections": standard_info.get("sections", []),
                "references": standard_info.get("references", []),
                "scope": standard_info.get("scope"),
                "normative_references": standard_info.get("normative_references", []),
                "definitions": standard_info.get("definitions", []),
            })
            
            if self.extract_cross_references:
                cross_refs = self._extract_cross_references(full_text)
                metadata.custom["cross_references"] = cross_refs
            
            if self.detect_sections:
                sections = self._extract_sections(full_text)
                metadata.custom["structured_sections"] = sections
            
            metadata.keywords = self._extract_keywords(full_text, standard_info)
            
            chunks = self._chunk_by_sections(full_text, metadata)
            
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
            logger.error(f"Erreur d'ingestion de norme: {e}")
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
    
    def _extract_text(self, file_path: str) -> str:
        """Extrait le texte du document"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except ImportError:
            with open(file_path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Erreur d'extraction: {e}")
            return f"[Norme: {os.path.basename(file_path)}]"
    
    def _extract_standard_info(self, text: str, file_path: str) -> Dict[str, Any]:
        """Extrait les informations de la norme"""
        info = {
            "code": None,
            "type": None,
            "organization": None,
            "title": None,
            "version": None,
            "date": None,
            "sections": [],
            "references": [],
            "scope": None,
            "normative_references": [],
            "definitions": []
        }
        
        first_500 = text[:500]
        
        for std_type, pattern in self.STANDARD_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["type"] = std_type
                info["organization"] = std_type
                info["code"] = match.group(0).strip()
                break
        
        if not info["code"]:
            filename = os.path.basename(file_path)
            for std_type, pattern in self.STANDARD_PATTERNS.items():
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    info["type"] = std_type
                    info["organization"] = std_type
                    info["code"] = match.group(0).strip()
                    break
        
        title_patterns = [
            r'(?:titre|title|subject)\s*:?\s*(.+?)(?:\n|$)',
            r'(?:objet|scope)\s*:?\s*(.+?)(?:\n|$)',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, first_500, re.IGNORECASE)
            if match:
                info["title"] = match.group(1).strip()
                break
        
        version_patterns = [
            r'version\s*[vV]?\.?\s*(\d+[\.\d]*)',
            r'edition\s*[vV]?\.?\s*(\d+[\.\d]*)',
        ]
        for pattern in version_patterns:
            match = re.search(pattern, first_500, re.IGNORECASE)
            if match:
                info["version"] = match.group(1)
                break
        
        date_match = re.search(r'(?:date|year)\s*:?\s*(\d{4})', first_500, re.IGNORECASE)
        if date_match:
            info["date"] = date_match.group(1)
        
        section_matches = re.findall(
            r'(?:section|chapitre|article|clause)\s*(\d+)\s*[.:]\s*(.+?)(?:\n|$)',
            text[:2000],
            re.IGNORECASE
        )
        if section_matches:
            info["sections"] = [f"{num}: {title[:80]}" for num, title in section_matches]
        
        return info
    
    def _extract_cross_references(self, text: str) -> List[str]:
        """Extrait les références croisées"""
        references = []
        
        ref_patterns = [
            r'(?:cf\.?|voir|see|reference|refer to)\s+([A-Z]{2,4}\s*\d{3,5})',
            r'(?:cf\.?|voir|see|reference|refer to)\s+([A-Z]{2,4}\s*\d{3,5}\.\d+)',
        ]
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.extend(matches)
        
        return list(set(references))
    
    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Extrait les sections structurées"""
        sections = []
        
        section_patterns = [
            r'(?:section|article|clause)\s*(\d+)\s*[.:]\s*([^\n]+)\s*\n(.*?)(?=\n(?:section|article|clause)\s*\d+|\Z)',
        ]
        
        for pattern in section_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                for num, title, content in matches[:10]:
                    sections.append({
                        "number": num,
                        "title": title.strip(),
                        "content": content.strip()[:500]
                    })
                break
        
        return sections
    
    def _extract_keywords(self, text: str, info: Dict) -> List[str]:
        """Extrait les mots-clés"""
        keywords = set()
        
        if info.get("code"):
            keywords.add(info["code"])
        if info.get("type"):
            keywords.add(info["type"])
        
        tech_keywords = [
            "Ethernet", "Fiber", "Cable", "Connector", "Interface",
            "Protocol", "Network", "Security", "Performance",
        ]
        
        text_upper = text.upper()
        for kw in tech_keywords:
            if kw.upper() in text_upper:
                keywords.add(kw)
        
        return list(keywords)
    
    def _chunk_by_sections(self, text: str, metadata: ExtractedMetadata) -> List:
        """Découpe la norme par sections"""
        from .schemas import ExtractedChunk
        
        chunks = []
        sections = metadata.custom.get("structured_sections", [])
        
        if sections:
            for i, section in enumerate(sections):
                chunk_metadata = {
                    "document_id": metadata.custom.get("document_id"),
                    "section_number": section.get("number"),
                    "section_title": section.get("title"),
                    "chunk_type": "standard_section",
                }
                
                chunks.append(ExtractedChunk(
                    id=f"{metadata.custom.get('document_id', 'std')}_section_{i}",
                    content=f"Section {section.get('number')}: {section.get('title')}\n\n{section.get('content', '')}",
                    metadata=chunk_metadata
                ))
        
        if not chunks:
            chunks = self._chunk_text(text, {
                "document_id": metadata.custom.get("document_id"),
                "document_type": DocumentType.STANDARD.value
            })
        
        return chunks