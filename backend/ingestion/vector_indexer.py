"""
Indexation vectorielle pour les documents ingérés
"""

import logging
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)


class VectorIndexer:
    """Interface d'indexation vectorielle (ChromaDB)"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.collection_name = self.config.get("collection_name", "knowledge_base")
        self.chroma_client = self.config.get("chroma_client")
        self.embedding_function = self.config.get("embedding_function")
        self._collection = None
    
    def _get_collection(self):
        """Récupère ou crée la collection ChromaDB"""
        if self._collection is None and self.chroma_client:
            try:
                # Essayer de récupérer la collection existante
                self._collection = self.chroma_client.get_collection(self.collection_name)
            except:
                # Créer une nouvelle collection
                self._collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
        return self._collection
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Ajoute un document à la base vectorielle"""
        collection = self._get_collection()
        if not collection:
            logger.warning("Collection ChromaDB non disponible")
            return str(uuid.uuid4())
        
        vector_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        try:
            collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[vector_id]
            )
            return vector_id
        except Exception as e:
            logger.error(f"Erreur d'indexation: {e}")
            return vector_id
    
    def add_documents(self, contents: List[str], metadatas: List[Dict[str, Any]]) -> List[str]:
        """Ajoute plusieurs documents à la base vectorielle"""
        collection = self._get_collection()
        if not collection:
            logger.warning("Collection ChromaDB non disponible")
            return [str(uuid.uuid4()) for _ in contents]
        
        vector_ids = [f"doc_{uuid.uuid4().hex[:8]}" for _ in contents]
        
        try:
            collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=vector_ids
            )
            return vector_ids
        except Exception as e:
            logger.error(f"Erreur d'indexation batch: {e}")
            return vector_ids
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recherche des documents similaires"""
        collection = self._get_collection()
        if not collection:
            logger.warning("Collection ChromaDB non disponible")
            return []
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=k
            )
            
            return [
                {
                    "content": doc,
                    "metadata": meta,
                    "distance": score
                }
                for doc, meta, score in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )
            ]
        except Exception as e:
            logger.error(f"Erreur de recherche: {e}")
            return []
    
    def delete_document(self, document_id: str):
        """Supprime un document de la base vectorielle"""
        collection = self._get_collection()
        if not collection:
            return
        
        try:
            # Supprimer tous les chunks associés au document
            # (à implémenter selon la structure)
            pass
        except Exception as e:
            logger.error(f"Erreur de suppression: {e}")