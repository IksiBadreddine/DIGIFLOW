"""
Vector Store Service

Local Vector Store using ChromaDB + HuggingFace Embeddings.
"""

import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


PRODUCTS_COLLECTION = "products_kb"
CDC_COLLECTION = "cdc_documents"


# ============================================================
# Embeddings
# ============================================================

@lru_cache(maxsize=1)
def get_embeddings():
    """
    Returns the configured embedding model.

    Uses cache to avoid reloading the model multiple times.
    """

    provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()

    if provider != "huggingface":
        raise ValueError(f"Unsupported embedding provider: {provider}")

    return HuggingFaceEmbeddings(
        model_name=os.getenv(
            "EMBEDDING_MODEL",
            "BAAI/bge-m3"
        ),
        model_kwargs={
            "device": "cpu"
        },
        encode_kwargs={
            "normalize_embeddings": True
        },
    )


# ============================================================
# Stores
# ============================================================

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


# ============================================================
# Indexation
# ============================================================

def index_products(
    docs: list[Document],
    persist_dir: str,
) -> Chroma:
    """
    Rebuilds the product knowledge base.
    """

    store = Chroma(
        collection_name=PRODUCTS_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )

    try:
        store.delete_collection()
    except Exception:
        pass

    return Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        collection_name=PRODUCTS_COLLECTION,
        persist_directory=persist_dir,
    )


def index_cdc(
    docs: list[Document],
    persist_dir: str,
    session_id: str,
) -> Chroma:
    """
    Indexes a customer specification document.
    """

    return Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        collection_name=f"cdc_{session_id}",
        persist_directory=persist_dir,
    )


# ============================================================
# Search
# ============================================================

def search_products(
    query: str,
    persist_dir: str,
    k: int = 4,
) -> list[Document]:
    """
    Product similarity search.
    """

    store = get_product_store(persist_dir)

    return store.similarity_search(
        query,
        k=k,
    )


def search_cdc(
    query: str,
    persist_dir: str,
    session_id: str,
    k: int = 6,
) -> list[Document]:
    """
    Similarity search inside one uploaded specification.
    """

    store = Chroma(
        collection_name=f"cdc_{session_id}",
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )

    return store.similarity_search(
        query,
        k=k,
    )