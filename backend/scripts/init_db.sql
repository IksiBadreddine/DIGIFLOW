-- backend/scripts/init_db.sql

-- Créer les extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    file_size INTEGER,
    mime_type VARCHAR(100),
    document_type VARCHAR(50),
    category VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Métadonnées
    title VARCHAR(500),
    author VARCHAR(200),
    publication_date TIMESTAMP,
    page_count INTEGER,
    language VARCHAR(10),
    tags JSONB DEFAULT '[]',  -- ✅ CHANGÉ : text[] → JSONB
    
    -- Champs spécifiques
    manufacturer VARCHAR(200),
    standard_code VARCHAR(100),
    project_id VARCHAR(100),   -- ✅ CHANGÉ : UUID → VARCHAR
    session_id VARCHAR(100),   -- ✅ CHANGÉ : UUID → VARCHAR
    
    -- Contenu
    full_text TEXT,
    chunk_count INTEGER DEFAULT 0,
    word_count INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Table: document_chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(100) PRIMARY KEY,   -- ✅ CHANGÉ : UUID → VARCHAR
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64),
    
    -- Métadonnées
    page_number INTEGER,
    section_title VARCHAR(500),
    section_number VARCHAR(50),
    chunk_type VARCHAR(50),
    start_char INTEGER,
    end_char INTEGER,
    vector_id VARCHAR(100),
    chunk_metadata JSONB DEFAULT '{}',  -- ✅ CHANGÉ : metadata → chunk_metadata
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: document_meta
CREATE TABLE IF NOT EXISTS document_meta (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    value_type VARCHAR(50),
    json_value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, key)
);

-- Table: projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_code VARCHAR(50) UNIQUE NOT NULL,
    project_name VARCHAR(500) NOT NULL,
    project_description TEXT,
    client_name VARCHAR(200),
    client_id VARCHAR(100),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    main_rfp_id UUID,
    main_boq_id UUID,
    compliance_score DECIMAL(5,2),
    offer_generated_at TIMESTAMP,
    project_metadata JSONB DEFAULT '{}',  -- ✅ CHANGÉ : metadata → project_metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: products (catalogue dynamique)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    manufacturer VARCHAR(200),
    reference VARCHAR(200),
    category VARCHAR(100),
    specs JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]', 
    datasheet_summary TEXT,
    datasheet_document_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_products_manufacturer ON products(manufacturer);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_product_id ON products(product_id);

-- Table: sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    main_document_id UUID REFERENCES documents(id),
    current_step INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    analysis_result JSONB,
    selected_products JSONB,
    generated_offer JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: ingestion_logs
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    source_type VARCHAR(50),
    source_path TEXT,
    ingestor_used VARCHAR(100),
    processing_time INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    warning_messages JSONB,
    chunks_generated INTEGER,
    tables_extracted INTEGER,
    images_extracted INTEGER,
    ocr_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_manufacturer ON documents(manufacturer);
CREATE INDEX idx_documents_standard_code ON documents(standard_code);
CREATE INDEX idx_documents_session_id ON documents(session_id);
CREATE INDEX idx_documents_project_id ON documents(project_id);

CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_vector_id ON document_chunks(vector_id);

CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- Fonction pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE '✅ Base de données initialisée avec succès !';
    RAISE NOTICE '📊 Tables créées: documents, document_chunks, document_meta, projects, sessions, ingestion_logs';
END $$;