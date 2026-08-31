# backend/services/product_service.py

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy import or_

from models.database import SessionLocal
from models.database import Product

logger = logging.getLogger(__name__)


class ProductService:
    """Service de gestion du catalogue produits (PostgreSQL)"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def create_or_update_product(
        self,
        product_id: str,
        name: str,
        manufacturer: str,
        reference: str,
        category: str = "network_device",
        specs: Dict = None,
        tags: List[str] = None,
        datasheet_summary: str = "",
        datasheet_document_id: str = None
    ) -> str:
        """
        Crée ou met à jour un produit dans le catalogue
        """
        specs = specs or {}
        tags = tags or []
        
        # Vérifier si le produit existe déjà
        existing = self.db.query(Product).filter(
            Product.product_id == product_id
        ).first()
        
        if existing:
            # Mettre à jour
            existing.name = name
            existing.manufacturer = manufacturer
            existing.reference = reference
            existing.category = category
            existing.specs = specs
            existing.tags = tags
            existing.datasheet_summary = datasheet_summary
            existing.datasheet_document_id = datasheet_document_id
            existing.updated_at = datetime.now()
            self.db.commit()
            logger.info(f"✅ Produit mis à jour: {product_id}")
            return existing.id
        else:
            # Créer
            product = Product(
                id=str(uuid.uuid4()),
                product_id=product_id,
                name=name,
                manufacturer=manufacturer,
                reference=reference,
                category=category,
                specs=specs,
                tags=tags,
                datasheet_summary=datasheet_summary,
                datasheet_document_id=datasheet_document_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(product)
            self.db.commit()
            logger.info(f"✅ Produit créé: {product_id}")
            return product.id
    
    def get_all_products(self) -> List[Dict]:
        """Récupère tous les produits du catalogue"""
        products = self.db.query(Product).all()
        return [self._to_dict(p) for p in products]
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Récupère un produit par son ID"""
        product = self.db.query(Product).filter(
            Product.product_id == product_id
        ).first()
        return self._to_dict(product) if product else None
    
    def search_products(self, query: str, limit: int = 10) -> List[Dict]:
        """Recherche des produits par nom ou fabricant"""
        products = self.db.query(Product).filter(
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.manufacturer.ilike(f"%{query}%"),
                Product.reference.ilike(f"%{query}%")
            )
        ).limit(limit).all()
        return [self._to_dict(p) for p in products]
    
    def delete_product(self, product_id: str) -> bool:
        """Supprime un produit"""
        product = self.db.query(Product).filter(
            Product.product_id == product_id
        ).first()
        if product:
            self.db.delete(product)
            self.db.commit()
            logger.info(f"✅ Produit supprimé: {product_id}")
            return True
        return False
    
    def _to_dict(self, product) -> Dict:
        """Convertit un objet Product en dictionnaire"""
        return {
            "id": product.product_id,
            "name": product.name,
            "manufacturer": product.manufacturer,
            "reference": product.reference,
            "category": product.category,
            "specs": product.specs,
            "tags": product.tags,
            "datasheet_summary": product.datasheet_summary,
            "datasheet_document_id": product.datasheet_document_id
        }
    
    def close(self):
        self.db.close()