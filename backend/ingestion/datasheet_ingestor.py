"""
Ingestor pour Datasheets fabricants
"""

import os
import re
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from .base import BaseIngestor
from .schemas import ExtractedDocument, ExtractedMetadata, DocumentType, DocumentStatus
from services.product_service import ProductService
from services.llm_service import get_llm

logger = logging.getLogger(__name__)


class DatasheetIngestor(BaseIngestor):
    """Ingestor spécialisé pour les datasheets fabricants"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.manufacturers = self.config.get("manufacturers", [
            "cisco", "hpe", "aruba", "alcatel", "huawei", "juniper", 
            "dell", "lenovo", "ibm", "hp", "netgear", "d-link"
        ])
        self.use_llm = self.config.get("use_llm", True)  # ✅ Activer/désactiver le LLM
    
    def can_handle(self, file_path: str, original_filename: str = None) -> bool:
        """Détecte si c'est un datasheet"""
        if not file_path.lower().endswith('.pdf'):
            return False
        
        # ✅ Utiliser le nom original si disponible
        filename = original_filename or os.path.basename(file_path)
        filename = filename.lower()
        
        logger.info(f"🔍 Vérification datasheet: {filename}")
        
        # 1. Détection par nom de fichier
        keywords = ['datasheet', 'data sheet']
        if any(kw in filename for kw in keywords):
            logger.info(f"✅ Datasheet détecté par nom: {filename}")
            return True
        
        # 2. Détection par contenu
        try:
            with open(file_path, 'rb') as f:
                content = f.read(2000).decode('utf-8', errors='ignore')
                content_upper = content.upper()
                
                datasheet_keywords = [
                    'DATASHEET', 'DATA SHEET', 'PRODUCT SPECIFICATION',
                    'MODEL:', 'PART NUMBER:', 'ORDERING INFORMATION'
                ]
                if any(kw in content_upper for kw in datasheet_keywords):
                    logger.info(f"✅ Datasheet détecté par contenu: {filename}")
                    return True
        except:
            pass
        
        return False
    
    def _extract_with_llm(self, text: str, file_path: str) -> dict:
        """✅ Extrait les informations du datasheet avec un LLM"""
        
        # Limiter le texte pour éviter de dépasser le contexte
        text_truncated = text[:6000]
        
        prompt = f"""
        Analyse ce datasheet et extrait les informations suivantes en JSON.
        
        Texte du datasheet :
        {text_truncated}
        
        Réponds UNIQUEMENT en JSON valide avec cette structure EXACTE :
        {{
            "product_name": "Nom complet du produit",
            "manufacturer": "Nom du fabricant",
            "reference": "Référence produit",
            "category": "catégorie (switch, camera, ups, cable, rack, server, firewall)",
            "specs": {{
                "ports": "Nombre et type de ports",
                "poe": "Spécifications PoE",
                "power": "Alimentation",
                "weight": "Poids",
                "dimensions": "Dimensions",
                "temperature": "Température de fonctionnement"
            }},
            "tags": ["mot1", "mot2", "mot3"]
        }}
        
        IMPORTANT : Si une information n'est pas disponible, mets une chaîne vide "".
        """
        
        try:
            llm = get_llm(temperature=0.0)
            response = llm.invoke(prompt)
            
            # Nettoyer la réponse (enlever les marqueurs markdown)
            raw = response.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            
            result = json.loads(raw)
            logger.info(f"✅ Extraction LLM réussie pour {file_path}")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Échec de l'extraction LLM, fallback sur regex: {e}")
            # ✅ Fallback sur les méthodes statiques
            return {
                "product_name": self._extract_product_name(text, file_path),
                "manufacturer": self._detect_manufacturer(text, file_path),
                "reference": self._extract_product_reference(text, file_path),
                "category": self._extract_category(text, {}),
                "specs": self._extract_specifications(text),
                "tags": self._extract_keywords(text, {})
            }
    
    def ingest(self, file_path: str) -> ExtractedDocument:
        """Ingère un datasheet et ajoute le produit au catalogue"""
        logger.info(f"Ingestion du datasheet: {file_path}")
        
        doc_type = DocumentType.PDF_DATASHEET
        metadata = self._extract_metadata(file_path, doc_type)
        
        try:
            full_text = self._extract_text(file_path)
            
            # ✅ Utiliser le LLM pour l'extraction
            if self.use_llm:
                extracted = self._extract_with_llm(full_text, file_path)
            else:
                # Fallback statique
                extracted = {
                    "product_name": self._extract_product_name(full_text, file_path),
                    "manufacturer": self._detect_manufacturer(full_text, file_path),
                    "reference": self._extract_product_reference(full_text, file_path),
                    "category": self._extract_category(full_text, {}),
                    "specs": self._extract_specifications(full_text),
                    "tags": self._extract_keywords(full_text, {})
                }
            
            # ✅ Utiliser les valeurs extraites
            manufacturer = extracted.get("manufacturer", "Unknown")
            product_name = extracted.get("product_name", os.path.basename(file_path))
            product_ref = extracted.get("reference", "")
            category = extracted.get("category", "network_device")
            specs = extracted.get("specs", {})
            keywords = extracted.get("tags", [])
            
            # ✅ Mettre à jour les métadonnées
            metadata.manufacturer = manufacturer
            metadata.custom["specifications"] = specs
            metadata.custom["product_reference"] = product_ref
            metadata.custom["category"] = category
            metadata.keywords = keywords
            
            chunks = self._chunk_text(full_text, {
                "document_id": self._generate_document_id(file_path),
                "document_type": doc_type.value,
                "filename": os.path.basename(file_path),
                "manufacturer": manufacturer,
                "product_reference": product_ref
            })
            
            # ✅ Créer le document
            doc = ExtractedDocument(
                id=self._generate_document_id(file_path),
                filename=os.path.basename(file_path),
                file_path=file_path,
                document_type=doc_type,
                metadata=metadata,
                full_text=full_text,
                chunks=chunks,
                status=DocumentStatus.COMPLETED
            )
            
            # ✅ AJOUTER LE PRODUIT AU CATALOGUE
            try:
                product_service = ProductService()
                
                # ✅ Utiliser l'ID généré par le LLM ou le fallback
                product_id = product_ref or self._generate_product_id(manufacturer, product_name)
                
                product_service.create_or_update_product(
                    product_id=product_id,
                    name=product_name,
                    manufacturer=manufacturer,
                    reference=product_ref,
                    category=category,
                    specs=specs,
                    tags=keywords,
                    datasheet_summary=full_text[:500],
                    datasheet_document_id=doc.id
                )
                product_service.close()
                logger.info(f"✅ Produit ajouté au catalogue: {product_name} ({manufacturer})")
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur d'ajout au catalogue: {e}")
                # Ne pas bloquer l'ingestion si le catalogue échoue
            
            return doc
            
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

    # ============ MÉTHODES STATIQUES DE FALLBACK ============

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
        """Détecte le fabricant (fallback)"""
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
            "Hikvision": r"hikvision",
            "APC": r"apc|american power conversion",
        }
        
        for name, pattern in patterns.items():
            if re.search(pattern, text_lower):
                return name
        
        return "Unknown"
    
    def _extract_specifications(self, text: str) -> Dict[str, Any]:
        """Extrait les spécifications (fallback)"""
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
        """Extrait la référence produit (fallback)"""
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
    
    def _extract_product_name(self, text: str, file_path: str) -> str:
        """Extrait le nom du produit (fallback)"""
        filename = os.path.basename(file_path)
        
        patterns = [
            r'product\s*name\s*:?\s*(.+?)(?:\n|$)',
            r'model\s*name\s*:?\s*(.+?)(?:\n|$)',
            r'title\s*:?\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
    
    def _extract_category(self, text: str, specs: Dict) -> str:
        """Extrait la catégorie (fallback)"""
        categories = {
            "switch": ["switch", "switching", "ethernet"],
            "router": ["router", "routing"],
            "firewall": ["firewall", "security"],
            "camera": ["camera", "caméra", "dôme", "dome", "vidéo"],
            "ups": ["ups", "onduleur", "smart-ups"],
            "access_point": ["access point", "ap", "wireless"],
            "controller": ["controller", "wlc"],
            "cable": ["cable", "câble", "cat6", "utp"],
            "rack": ["rack", "baie", "19\""],
            "connector": ["rj45", "connectique", "connector"],
        }
        
        text_lower = text.lower()
        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return "network_device"
    
    def _extract_keywords(self, text: str, specs: Dict) -> List[str]:
        """Extrait les mots-clés (fallback)"""
        keywords = set()
        
        common_keywords = [
            "Ethernet", "Gigabit", "PoE", "PoE+", "PoE++",
            "Fiber", "SFP", "SFP+", "QSFP",
            "VLAN", "STP", "RSTP", "SNMP",
            "IPv4", "IPv6", "DHCP", "DNS",
            "SSL", "TLS", "IPSec", "VPN",
            "4MP", "IR", "Dôme", "Dome"
        ]
        
        text_upper = text.upper()
        for kw in common_keywords:
            if kw.upper() in text_upper:
                keywords.add(kw)
        
        return list(keywords)
    
    def _generate_product_id(self, manufacturer: str, name: str) -> str:
        """Génère un ID produit à partir du fabricant et du nom"""
        import re
        mfr = re.sub(r'[^a-zA-Z0-9]', '-', manufacturer.lower())
        name_clean = re.sub(r'[^a-zA-Z0-9]', '-', name.lower())
        return f"{mfr}-{name_clean[:30]}"