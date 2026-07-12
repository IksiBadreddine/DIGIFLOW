"""
Ingestor pour Datasheets fabricants
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class DatasheetIngestor(BaseIngestor):
    """Ingestor spécialisé pour les datasheets fabricants"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.manufacturers = self.config.get("manufacturers", [
            "cisco", "hpe", "aruba", "alcatel", "huawei", "juniper", 
            "dell", "lenovo", "ibm", "hp", "netgear", "d-link"
        ])
    
    def can_handle(self, file_path: str) -> bool:
        """Détecte si c'est un datasheet"""
        if not file_path.lower().endswith('.pdf'):
            return False
        
        filename = os.path.basename(file_path).lower()
        
        # 1. Détection par nom de fichier
        keywords = ['datasheet', 'data sheet']
        if any(kw in filename for kw in keywords):
            return True
        
        # 2. Détection par contenu
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1000).decode('utf-8', errors='ignore')
                content_upper = content.upper()
                
                datasheet_keywords = [
                    'DATASHEET', 'DATA SHEET', 'PRODUCT SPECIFICATION',
                    'MODEL:', 'PART NUMBER:', 'ORDERING INFORMATION'
                ]
                if any(kw in content_upper for kw in datasheet_keywords):
                    return True
        except:
            pass
        
        return False
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un datasheet"""
        logger.info(f"Ingestion du datasheet: {file_path}")
        
        doc_type = DocumentType.PDF_DATASHEET
        metadata = self._extract_metadata(file_path, doc_type)
        
        try:
            full_text = self._extract_text(file_path)
            
            manufacturer = self._detect_manufacturer(full_text, file_path)
            metadata.manufacturer = manufacturer
            
            specs = self._extract_specifications(full_text)
            metadata.custom["specifications"] = specs
            
            product_ref = self._extract_product_reference(full_text, file_path)
            metadata.custom["product_reference"] = product_ref
            
            category = self._extract_category(full_text, specs)
            metadata.custom["category"] = category
            
            keywords = self._extract_keywords(full_text, specs)
            metadata.keywords = keywords
            
            chunks = self._chunk_text(full_text, {
                "document_id": self._generate_document_id(file_path),
                "document_type": doc_type.value,
                "filename": os.path.basename(file_path),
                "manufacturer": manufacturer,
                "product_reference": product_ref
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
            logger.error(f"Erreur d'ingestion datasheet: {e}")
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
        """Extrait le texte du datasheet"""
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
            return f"[Datasheet: {os.path.basename(file_path)}]"
    
    def _detect_manufacturer(self, text: str, file_path: str) -> str:
        """Détecte le fabricant"""
        text_lower = text.lower()
        filename = os.path.basename(file_path).lower()
        
        for mfg in self.manufacturers:
            if mfg in text_lower or mfg in filename:
                return mfg.upper()
        
        patterns = {
            "Cisco": r"cisco systems?",
            "HPE": r"hewlett packard enterprise",
            "Aruba": r"aruba networks?",
            "Juniper": r"juniper networks?",
        }
        
        for name, pattern in patterns.items():
            if re.search(pattern, text_lower):
                return name
        
        return "Unknown"
    
    def _extract_specifications(self, text: str) -> Dict[str, Any]:
        """Extrait les spécifications"""
        specs = {}
        
        patterns = {
            "ports": r"(\d+)\s*(?:ports?|gigabit ports?)",
            "poe": r"poe(\+?)\s*(\d+)?\s*watts?",
            "power": r"power\s*(?:consumption|supply)\s*:?\s*([\d.]+)\s*w",
            "weight": r"weight\s*:?\s*([\d.]+)\s*(?:kg|lbs)",
            "temperature": r"temperature\s*:?\s*([\d.]+)\s*-\s*([\d.]+)\s*°c",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                specs[key] = match.group(0).strip()
        
        return specs
    
    def _extract_product_reference(self, text: str, file_path: str) -> str:
        """Extrait la référence produit"""
        filename = os.path.basename(file_path)
        
        patterns = [
            r'[A-Z]{2,5}-[A-Z0-9]{4,10}',
            r'[A-Z]{2,5}[0-9]{2,5}[A-Z]?',
            r'REF\s*:?\s*([A-Z0-9-]+)',
            r'Model\s*:?\s*([A-Z0-9-]+)',
            r'Part\s*Number\s*:?\s*([A-Z0-9-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return os.path.splitext(filename)[0]
    
    def _extract_category(self, text: str, specs: Dict) -> str:
        """Extrait la catégorie"""
        categories = {
            "switch": ["switch", "switching", "ethernet"],
            "router": ["router", "routing"],
            "firewall": ["firewall", "security"],
            "access_point": ["access point", "ap", "wireless"],
            "controller": ["controller", "wlc"],
        }
        
        text_lower = text.lower()
        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return "network_device"
    
    def _extract_keywords(self, text: str, specs: Dict) -> List[str]:
        """Extrait les mots-clés"""
        keywords = set()
        
        common_keywords = [
            "Ethernet", "Gigabit", "PoE", "PoE+", "PoE++",
            "Fiber", "SFP", "SFP+", "QSFP",
            "VLAN", "STP", "RSTP", "SNMP",
            "IPv4", "IPv6", "DHCP", "DNS",
            "SSL", "TLS", "IPSec", "VPN"
        ]
        
        text_upper = text.upper()
        for kw in common_keywords:
            if kw.upper() in text_upper:
                keywords.add(kw)
        
        return list(keywords)