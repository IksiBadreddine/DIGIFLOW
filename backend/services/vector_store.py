"""
Vector Store Service
Wraps ChromaDB for product knowledge base indexing and similarity search.
"""
import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


PRODUCTS_COLLECTION = "products_kb"
CDC_COLLECTION = "cdc_documents"


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


def get_product_store(persist_dir: str) -> Chroma:
    return Chroma(
        collection_name=PRODUCTS_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )


def get_cdc_store(persist_dir: str) -> Chroma:
    return Chroma(
        collection_name=CDC_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )


def index_products(docs: list[Document], persist_dir: str) -> Chroma:
    """Index product catalog into ChromaDB. Replaces existing collection."""
    store = Chroma(
        collection_name=PRODUCTS_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )
    # Clear existing and re-index
    try:
        store.delete_collection()
    except Exception:
        pass
    store = Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        collection_name=PRODUCTS_COLLECTION,
        persist_directory=persist_dir,
    )
    return store


def index_cdc(docs: list[Document], persist_dir: str, session_id: str) -> Chroma:
    """Index a user-uploaded CdC document into ChromaDB."""
    store = Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        collection_name=f"cdc_{session_id}",
        persist_directory=persist_dir,
    )
    return store


def search_products(query: str, persist_dir: str, k: int = 4) -> list[Document]:
    """Similarity search in product knowledge base."""
    store = get_product_store(persist_dir)
    return store.similarity_search(query, k=k)


def search_cdc(query: str, persist_dir: str, session_id: str, k: int = 6) -> list[Document]:
    """Similarity search in a specific CdC session."""
    store = Chroma(
        collection_name=f"cdc_{session_id}",
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )
    return store.similarity_search(query, k=k)
