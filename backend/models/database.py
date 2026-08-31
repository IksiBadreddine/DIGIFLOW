# backend/models/database.py

import os
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://digiflow:digiflow123@localhost:5432/digiflow"  # ← localhost par défaut
)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Base de données initialisée")

class Document(Base):
    __tablename__ = "documents"
    id = Column(String(36), primary_key=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_hash = Column(String(64), unique=True)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    document_type = Column(String(50))
    category = Column(String(50))
    status = Column(String(50), default="pending")
    title = Column(String(500))
    author = Column(String(200))
    publication_date = Column(DateTime)
    page_count = Column(Integer)
    language = Column(String(10))
    tags = Column(JSON, default=list)
    manufacturer = Column(String(200))
    standard_code = Column(String(100))
    project_id = Column(String(36))
    session_id = Column(String(36))
    full_text = Column(Text)
    chunk_count = Column(Integer, default=0)
    word_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    processed_at = Column(DateTime)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    # ✅ Changer le type de la colonne id
    id = Column(String(100), primary_key=True)  # Au lieu de String(36)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64))
    page_number = Column(Integer)
    section_title = Column(String(500))
    section_number = Column(String(50))
    chunk_type = Column(String(50))
    start_char = Column(Integer)
    end_char = Column(Integer)
    vector_id = Column(String(100))
    chunk_metadata = Column(JSON, default={})  # ✅ Renommé
    created_at = Column(DateTime, default=datetime.now)

class DocumentMeta(Base):
    __tablename__ = "document_meta"
    # ✅ Utiliser String pour l'ID (compatible avec UUID généré en Python)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    key = Column(String(100), nullable=False)
    value = Column(Text)
    value_type = Column(String(50))
    json_value = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (UniqueConstraint('document_id', 'key'),)

class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True)
    project_code = Column(String(50), unique=True, nullable=False)
    project_name = Column(String(500), nullable=False)
    project_description = Column(Text)
    client_name = Column(String(200))
    client_id = Column(String(100))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String(50), default="active")
    main_rfp_id = Column(String(36))
    main_boq_id = Column(String(36))
    compliance_score = Column(Float)
    offer_generated_at = Column(DateTime)
    project_metadata = Column(JSON, default={})  # ✅ Renommé
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True)
    product_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    manufacturer = Column(String(200))
    reference = Column(String(200))
    category = Column(String(100))
    specs = Column(JSON, default={})
    tags = Column(JSON, default=list)
    datasheet_summary = Column(Text)
    datasheet_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(100))
    main_document_id = Column(String(36), ForeignKey("documents.id"))
    current_step = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    analysis_result = Column(JSON)
    selected_products = Column(JSON)
    generated_offer = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    source_type = Column(String(50))
    source_path = Column(Text)
    ingestor_used = Column(String(100))
    processing_time = Column(Integer)
    status = Column(String(50))
    error_message = Column(Text)
    warning_messages = Column(JSON, default=list)
    chunks_generated = Column(Integer)
    tables_extracted = Column(Integer)
    images_extracted = Column(Integer)
    ocr_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)