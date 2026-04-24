"""
Document Ingestion Service
Handles PDF and DOCX parsing, text extraction, and chunking
for RAG indexing.
"""
import os
import json
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def extract_text_from_docx(path: str) -> str:
    doc = DocxDocument(path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(path: str) -> str:
    """Route to the correct extractor based on file extension."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(path)
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, filename: str) -> list[Document]:
    """Split text into overlapping chunks for vector indexing."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [
        Document(page_content=chunk, metadata={"source": filename, "chunk": i})
        for i, chunk in enumerate(chunks)
    ]


def load_product_catalog(catalog_path: str) -> list[Document]:
    """Load product catalog JSON as LangChain Documents for indexing."""
    with open(catalog_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    docs = []
    for p in products:
        content = (
            f"PRODUIT: {p['name']}\n"
            f"Fabricant: {p['manufacturer']}\n"
            f"Référence: {p['reference']}\n"
            f"Catégorie: {p['category']}\n"
            f"Tags: {', '.join(p['tags'])}\n"
            f"Description: {p['datasheet_summary']}\n"
            f"Spécifications: {json.dumps(p['specs'], ensure_ascii=False, indent=2)}"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "source": "product_catalog",
                "product_id": p["id"],
                "reference": p["reference"],
                "manufacturer": p["manufacturer"],
                "category": p["category"],
            }
        ))
    return docs, products
