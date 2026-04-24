# PresalesAI — Plateforme IA de Génération d'Offres Techniques

> Plateforme end-to-end pour générer automatiquement des offres techniques conformes
> à partir d'un Cahier des Charges (ICT / ELV / Télécom / Sécurité).

---

## Architecture

```
presales-ai/
├── backend/                     # FastAPI + LangChain + ChromaDB
│   ├── main.py                  # Point d'entrée FastAPI
│   ├── routers/
│   │   ├── analyze.py           # POST /api/analyze   — upload + extraction
│   │   └── offer.py             # POST /api/generate-offer + GET /api/export/:id
│   ├── services/
│   │   ├── ingestion.py         # Extraction texte PDF/DOCX + chunking
│   │   ├── vector_store.py      # ChromaDB wrapper (index + search)
│   │   └── llm_service.py       # Chains GPT-4 (extraction, matching, génération)
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   ├── data/products/
│   │   └── catalog.json         # Base produits (à enrichir)
│   └── requirements.txt
│
├── frontend/                    # React + Vite
│   ├── src/
│   │   ├── App.jsx              # Orchestration 4 étapes (stepper)
│   │   ├── components/
│   │   │   ├── UploadZone.jsx   # Drag & drop upload + progress
│   │   │   ├── RequirementsPanel.jsx  # Affichage exigences extraites
│   │   │   ├── ProductsPanel.jsx      # Scoring produits + tableau conformité
│   │   │   └── OfferPanel.jsx         # Offre finale + BOQ + export DOCX
│   │   └── services/api.js      # Axios client
│   ├── vite.config.js           # Proxy /api → backend:8000
│   └── nginx.conf               # Prod: SPA + proxy
│
├── docker-compose.yml           # Déploiement full-stack
└── README.md
```

## Pipeline IA (étape par étape)

```
[PDF/DOCX/TXT]
      │
      ▼
 ingestion.py ──► Extraction texte ──► Chunking (800 tokens)
      │                                       │
      ▼                                       ▼
 llm_service.py                       vector_store.py
 GPT-4 EXTRACT_PROMPT                 ChromaDB index
      │                                       │
      ▼                                       │
 Requirements[]  ◄─────────────────── RAG context
      │
      ▼
 Pour chaque produit du catalog.json :
   GPT-4 MATCH_PROMPT → ComplianceRow[] + score
      │
      ▼
 GPT-4 OFFER_PROMPT → Offre technique complète
      │
      ▼
 [Affichage React] → [Export DOCX]
```

## Démarrage rapide

### Option A — Docker (recommandé)

```bash
# 1. Cloner le projet
git clone <repo-url> && cd presales-ai

# 2. Configurer la clé OpenAI
echo "OPENAI_API_KEY=sk-..." > .env
echo "OPENAI_MODEL=gpt-4o" >> .env

# 3. Lancer
docker-compose up --build

# Frontend : http://localhost:3000
# Backend  : http://localhost:8000
# API docs : http://localhost:8000/docs
```

### Option B — Développement local

**Backend :**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Éditer .env → mettre votre OPENAI_API_KEY

uvicorn main:app --reload --port 8000
```

**Frontend :**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## Enrichir le catalogue produits

Éditer `backend/data/products/catalog.json` — ajouter des produits :

```json
{
  "id": "mon-produit-id",
  "name": "Nom du produit",
  "manufacturer": "Fabricant",
  "reference": "REF-001",
  "category": "switch_access_indoor",
  "tags": ["switch", "poe", "24ports"],
  "specs": {
    "ports_rj45": 24,
    "switching_bandwidth_gbps": 88,
    ...
  },
  "datasheet_summary": "Description complète du produit incluant toutes les specs..."
}
```

Supprimer `backend/chroma_db/.products_indexed` pour forcer la réindexation.

## API Reference

| Méthode | Endpoint               | Description                              |
|---------|------------------------|------------------------------------------|
| GET     | `/health`              | Santé du service + config LLM            |
| POST    | `/api/analyze`         | Upload CdC → extraction + scoring        |
| GET     | `/api/session/{id}`    | Récupérer une session existante          |
| POST    | `/api/generate-offer`  | Générer l'offre technique complète       |
| GET     | `/api/export/{id}`     | Télécharger l'offre en DOCX              |

Documentation interactive : `http://localhost:8000/docs`

## Variables d'environnement

| Variable              | Défaut         | Description                    |
|-----------------------|----------------|--------------------------------|
| `OPENAI_API_KEY`      | —              | **Obligatoire**                |
| `OPENAI_MODEL`        | `gpt-4o`       | Modèle GPT-4 à utiliser        |
| `CHROMA_PERSIST_DIR`  | `./chroma_db`  | Répertoire ChromaDB            |
| `UPLOAD_DIR`          | `./uploads`    | Répertoire fichiers uploadés   |
| `MAX_FILE_SIZE_MB`    | `20`           | Taille max upload              |

## Évolutions prévues (Phase 2+)

- [ ] Authentification utilisateurs (JWT)
- [ ] Persistance sessions (Redis / PostgreSQL)
- [ ] Support images / schémas (OCR Tesseract)
- [ ] Modèle local (Ollama / LLaMA) en remplacement de GPT-4
- [ ] Génération de schémas réseau automatique
- [ ] Module d'administration catalogue produits (UI)
- [ ] Support BOQ Excel import/export
- [ ] Multi-langue (AR / EN / FR)
