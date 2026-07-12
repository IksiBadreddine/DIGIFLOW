"""
Service d'indexation vectorielle avec ChromaDB
Support Hugging Face pour les embeddings
"""

import os
import logging
import uuid
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingFunction:
    """Fonction d'embedding compatible avec ChromaDB"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle SentenceTransformer"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"🔄 Chargement du modèle: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"✅ Modèle chargé sur: {self._model.device}")
        except ImportError:
            logger.error("sentence-transformers non installé")
            raise
    
    def name(self) -> str:
        """Retourne le nom du modèle pour ChromaDB"""
        return self.model_name
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Calcule les embeddings pour une liste de textes.
        Signature attendue par ChromaDB pour l'indexation.
        """
        if isinstance(input, str):
            input = [input]
        
        if not input:
            return []
        
        # Générer les embeddings
        embeddings = self._model.encode(input)
        
        # Convertir en liste de listes de float
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()
        return embeddings
    
    def embed_query(self, input: str) -> List[float]:
        """
        Calcule l'embedding pour une requête unique.
        ✅ Signature CORRECTE : 'input' et non 'text'
        """
        if not input:
            return []
        
        embedding = self._model.encode(input)
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        return embedding


class VectorStore:
    """Service d'indexation vectorielle avec ChromaDB"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Configuration ChromaDB
        self.persist_dir = self.config.get(
            "persist_dir",
            os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        )
        
        # Configuration des embeddings
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "huggingface")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        
        logger.info(f"📚 Provider embeddings: {self.embedding_provider}")
        logger.info(f"📚 Modèle embeddings: {self.embedding_model}")
        
        # Créer la fonction d'embedding
        self.embedding_fn = HuggingFaceEmbeddingFunction(self.embedding_model)
        
        # Initialiser le client ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        logger.info(f"✅ ChromaDB initialisé: {self.persist_dir}")
    
    def get_or_create_collection(self, collection_name: str):
        """Récupère ou crée une collection"""
        try:
            return self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
        except:
            return self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
    
    def add_document(self, content: str, metadata: Dict[str, Any], collection: str = "knowledge_base") -> str:
        """Ajoute un document à la collection vectorielle"""
        
        collection_obj = self.get_or_create_collection(collection)
        
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        try:
            collection_obj.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            logger.debug(f"✅ Document ajouté: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"❌ Erreur d'ajout: {e}")
            raise
    
    def add_documents(self, contents: List[str], metadatas: List[Dict], collection: str = "knowledge_base") -> List[str]:
        """Ajoute plusieurs documents à la collection"""
        
        collection_obj = self.get_or_create_collection(collection)
        
        doc_ids = [f"doc_{uuid.uuid4().hex[:12]}" for _ in contents]
        
        try:
            collection_obj.add(
                documents=contents,
                metadatas=metadatas,
                ids=doc_ids
            )
            logger.info(f"✅ {len(doc_ids)} documents ajoutés")
            return doc_ids
        except Exception as e:
            logger.error(f"❌ Erreur d'ajout batch: {e}")
            raise
    
    def search(self, query: str, collection: str = "knowledge_base", n_results: int = 5) -> List[Dict]:
        """Recherche des documents par similarité sémantique"""
        
        collection_obj = self.get_or_create_collection(collection)
        
        try:
            results = collection_obj.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Formater les résultats
            documents = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None,
                        "id": results['ids'][0][i] if results['ids'] else None
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Erreur de recherche: {e}")
            return []
    
    def delete_collection(self, collection_name: str):
        """Supprime une collection"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"✅ Collection supprimée: {collection_name}")
        except Exception as e:
            logger.warning(f"⚠️ Collection non trouvée: {e}")
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """Retourne des informations sur une collection"""
        try:
            collection = self.client.get_collection(collection_name)
            return {
                "name": collection.name,
                "count": collection.count(),
                "metadata": collection.metadata
            }
        except:
            return {"name": collection_name, "count": 0, "metadata": {}}
    
    def list_collections(self) -> List[str]:
        """Liste toutes les collections"""
        return [col.name for col in self.client.list_collections()]