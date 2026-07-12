"""
Script pour indexer la base de connaissances dans ChromaDB
Avec indexation vectorielle
"""

import os
import sys
import logging
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import DocumentProcessor
from services.vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def index_knowledge_base():
    """
    Indexe tous les documents dans ChromaDB
    """
    logger.info("📚 Indexation vectorielle de la base de connaissances...")
    
    # 1. Initialiser les services
    vector_store = VectorStore()
    processor = DocumentProcessor(config={"vector_store": vector_store})
    
    # 2. Créer la collection une fois pour toutes
    collection_name = "knowledge_base"
    vector_store.get_or_create_collection(collection_name)
    logger.info(f"✅ Collection {collection_name} prête")
    
    # 3. Chemin de la base de connaissances
    kb_path = Path("data/knowledge_base")
    
    if not kb_path.exists():
        logger.error(f"❌ Dossier non trouvé: {kb_path}")
        return 0
    
    # 4. Indexer chaque dossier
    total_docs = 0
    total_chunks = 0
    
    for folder in kb_path.iterdir():
        if not folder.is_dir():
            continue
        
        logger.info(f"📁 Traitement: {folder.name}")
        
        # Compter les fichiers
        files = list(folder.glob("*"))
        if not files:
            logger.info(f"   ⚠️ Aucun fichier")
            continue
        
        logger.info(f"   📄 {len(files)} fichiers trouvés")
        
        for file_path in files:
            if not file_path.is_file():
                continue
            
            try:
                logger.info(f"   📄 {file_path.name}")
                
                # Traiter le fichier
                doc = processor.process_file(str(file_path))
                
                if doc and doc.status.value == "completed":
                    # ✅ Ajouter les chunks à ChromaDB
                    for chunk in doc.chunks:
                        try:
                            vector_store.add_document(
                                content=chunk.content,
                                metadata={
                                    "document_id": doc.id,
                                    "document_type": doc.document_type.value,
                                    "category": folder.name,
                                    "filename": doc.filename,
                                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                                    "source": "knowledge_base"
                                },
                                collection=collection_name
                            )
                        except Exception as e:
                            logger.warning(f"      ⚠️ Erreur d'ajout: {e}")
                            continue
                    
                    total_docs += 1
                    total_chunks += len(doc.chunks)
                    logger.info(f"      ✅ Type: {doc.document_type.value} - {len(doc.chunks)} chunks")
                else:
                    error = doc.error if doc else "Inconnu"
                    logger.warning(f"      ⚠️ Échec: {error}")
                    
            except Exception as e:
                logger.error(f"      ❌ Erreur: {e}")
        
        logger.info("")
    
    # Afficher les statistiques
    info = vector_store.get_collection_info(collection_name)
    logger.info(f"✅ Collection ChromaDB: {info['count']} vecteurs")
    logger.info(f"✅ Documents indexés: {total_docs}")
    logger.info(f"✅ Chunks indexés: {total_chunks}")
    
    return total_docs


def search_knowledge(query: str, n_results: int = 5):
    """
    Recherche dans la base de connaissances
    """
    logger.info(f"\n🔍 Recherche: '{query}'")
    logger.info("-" * 40)
    
    vector_store = VectorStore()
    results = vector_store.search(query, n_results=n_results)
    
    if not results:
        logger.info("   Aucun résultat")
        return
    
    for i, result in enumerate(results):
        logger.info(f"\n{i+1}. Score: {1 - result['distance']:.3f}")
        logger.info(f"   Type: {result['metadata'].get('document_type', 'inconnu')}")
        logger.info(f"   Fichier: {result['metadata'].get('filename', 'inconnu')}")
        logger.info(f"   Extrait: {result['content'][:200]}...")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", type=str, help="Rechercher dans la base")
    parser.add_argument("--n", type=int, default=5, help="Nombre de résultats")
    args = parser.parse_args()
    
    if args.search:
        search_knowledge(args.search, args.n)
    else:
        index_knowledge_base()