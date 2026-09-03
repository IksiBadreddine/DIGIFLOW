"""
LLM Analysis Service

Local AI implementation using Ollama.

Provides:
    1. Requirement extraction
    2. Product compliance matching
    3. Technical offer generation
"""

import json
import os
import re
import logging
from typing import List, Dict, Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# LLM
# ============================================================

def get_llm(temperature: float = 0.1) -> ChatOllama:
    """
    Returns the configured local LLM with optimized parameters.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

        # ✅ Utiliser OpenAI par défaut
    if provider == "openai":
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=120,  # 2 minutes
            max_retries=3,
        )
    
    # Fallback sur Ollama si spécifié
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("LLM_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )
    
    else:
        raise ValueError(f"Provider non supporté: {provider}")

def get_embeddings():
    """
    Returns the configured embeddings (OpenAI)
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    
    if provider == "openai":
        return OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    
    elif provider == "huggingface":
        # Garder Hugging Face comme fallback
        from sentence_transformers import SentenceTransformer
        
        class HuggingFaceEmbeddingFunction:
            def __init__(self, model_name):
                self.model = SentenceTransformer(model_name)
                self.model_name = model_name
            
            def __call__(self, texts):
                if isinstance(texts, str):
                    texts = [texts]
                return self.model.encode(texts).tolist()
        
        return HuggingFaceEmbeddingFunction(os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"))
    
    else:
        raise ValueError(f"Provider embeddings non supporté: {provider}")

# ============================================================
# JSON Helper - Version robuste
# ============================================================

def clean_json_response(raw: str) -> dict:
    """
    Extract and parse JSON returned by the LLM.
    Handles markdown code blocks and extra text.
    """
    # ✅ 1. Supprimer les marqueurs markdown (```json et ```)
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    
    # ✅ 2. Supprimer les préfixes "json" ou "assistant"
    raw = re.sub(r'^(?:json|assistant)\s*', '', raw, flags=re.IGNORECASE)
    
    # ✅ 3. Trouver le premier { et le dernier }
    start = raw.find("{")
    end = raw.rfind("}")
    
    if start == -1 or end == -1:
        raise ValueError(f"LLM did not return JSON.\n\nResponse:\n{raw[:500]}...")
    
    # ✅ 4. Extraire la partie JSON
    json_str = raw[start:end + 1]
    
    # ✅ 5. Nettoyer les caractères spéciaux
    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
    
    # ✅ 6. Tentative de parsing
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Erreur JSON initiale: {e}")
        
        # ✅ 7. Tentative de réparation
        try:
            # Remplacer les guillemets simples par des doubles
            json_fixed = re.sub(r"'([^']+)'", r'"\1"', json_str)
            
            # Supprimer les virgules en trop
            json_fixed = re.sub(r',\s*}', '}', json_fixed)
            json_fixed = re.sub(r',\s*]', ']', json_fixed)
            
            # Supprimer les sauts de ligne dans les chaînes
            json_fixed = re.sub(r'\n(?=[^"]*")', ' ', json_fixed)
            
            return json.loads(json_fixed)
        except json.JSONDecodeError as e2:
            logger.error(f"Erreur JSON après nettoyage: {e2}")
            logger.error(f"Contenu: {json_str[:500]}...")
            raise ValueError(f"Invalid JSON returned by the LLM.\n\n{json_str[:500]}...")


# ============================================================
# 1. REQUIREMENT EXTRACTION
# ============================================================

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Tu es un ingénieur avant-vente expert en réseaux, télécoms et sécurité (ICT/ELV).

Analyse le cahier des charges et extrais TOUTES les exigences techniques.

⚠️ IMPORTANT - RÈGLES STRICTES :
1. Réponds UNIQUEMENT en JSON valide
2. Le JSON doit être COMPLET et TERMINÉ avec }}
3. Sois EXHAUSTIF : extrais TOUTES les exigences
4. Structure obligatoire :

{{
  "summary": "Résumé concis du besoin en 3-4 phrases",
  "key_constraints": [
    "Contrainte technique majeure 1",
    "Contrainte technique majeure 2"
  ],
  "requirements": [
    {{
      "id": "REQ-001",
      "section": "Nom de la section",
      "description": "Description claire de l'exigence",
      "value": "Valeur spécifique si applicable"
    }}
  ]
}}

Inclus ces types d'exigences :
- Capacités et performances (débit, nombre de ports, etc.)
- Protocoles supportés (IEEE, SNMP, etc.)
- Sécurité (authentification, chiffrement, etc.)
- Alimentation (PoE, redondance, etc.)
- Environnement (température, humidité, etc.)
- Management (supervision, configuration, etc.)
- Redondance et haute disponibilité
- Contraintes d'installation

Génère le JSON COMPLET MAINTENANT :
""",
    ),
    (
        "human",
        """
CAHIER DES CHARGES À ANALYSER :

{cdc_text}

➡️ EXTRAIS TOUTES LES EXIGENCES EN JSON COMPLET :
""",
    ),
])


def extract_requirements(cdc_text: str) -> dict:
    """
    Extracts technical requirements from a specification document.
    Handles large documents by intelligent chunking.
    """
    logger.info(f"Extraction des exigences - Texte: {len(cdc_text)} caractères")
    
    # ✅ Gestion des longs documents : prendre les parties les plus importantes
    # On garde le début (généralement le plus important) et on ajoute un échantillon
    if len(cdc_text) > 8000:
        logger.info(f"Texte long ({len(cdc_text)} caractères) - Utilisation des 8000 premiers caractères")
        # Prendre les 8000 premiers caractères + un échantillon de la fin
        sample_start = cdc_text[:6000]
        sample_end = cdc_text[-2000:] if len(cdc_text) > 8000 else ""
        cdc_text = sample_start + "\n\n[... fin du document ...]\n\n" + sample_end
    
    llm = get_llm(temperature=0.0)
    chain = EXTRACT_PROMPT | llm | StrOutputParser()

    try:
        raw = chain.invoke({"cdc_text": cdc_text})
        
        # Logging pour debug
        logger.info(f"Réponse LLM reçue: {len(raw)} caractères")
        if len(raw) < 100:
            logger.warning(f"Réponse très courte: {raw}")
        
        return clean_json_response(raw)
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction: {e}")
        raise


# ============================================================
# 2. PRODUCT COMPLIANCE
# ============================================================
# MATCH_PROMPT = ChatPromptTemplate.from_messages([
#     (
#         "system",
#         """Tu es un ingénieur avant-vente expert en réseaux, télécoms et sécurité (ICT/ELV), spécialisé dans l'évaluation de conformité technique.

# Compare les exigences du cahier des charges avec les caractéristiques du produit proposé.

# ⚠️ RÈGLES STRICTES DE SCORING :
# 1. **CONFORME (100%)** : Le produit répond EXACTEMENT à l'exigence.
#    - Exemple : "24 ports" → produit a "24 ports Gigabit Ethernet"
#    - Exemple : "PoE+" → produit a "PoE+ 195W"
#    - Exemple : "VLAN 802.1Q" → produit a "802.1Q VLAN"

# 2. **PARTIEL (50%)** : Le produit répond PARTIELLEMENT.
#    - Exemple : "24 ports" → produit a "16 ports"
#    - Exemple : "PoE+ 370W" → produit a "PoE 150W"
#    - Exemple : "4 caméras" → produit a "1 caméra"

# 3. **NON_CONFORME (0%)** : Le produit NE répond PAS.
#    - Exemple : "24 ports" → produit a "8 ports"
#    - Exemple : "PoE+" → produit n'a pas de PoE

# 📌 RÈGLE CRITIQUE POUR LA RÉPONSE PRODUIT :
# Pour CHAQUE exigence, la réponse produit doit être la SPÉCIFICATION PRÉCISE du produit qui correspond.
# NE METS JAMAIS LA MÊME RÉPONSE POUR DEUX EXIGENCES DIFFÉRENTES.

# Exemple correct :
# Exigence : "24 ports Gigabit Ethernet" → Réponse : "24 x 10/100/1000 Mbps + 4 x SFP"
# Exigence : "Support VLAN" → Réponse : "802.1Q, jusqu'à 4094 VLAN"
# Exigence : "Supervision SNMP" → Réponse : "SNMP v1/v2c/v3, interface web, CLI"

# 📊 CALCUL DU SCORE GLOBAL :
# - Score = (somme des scores individuels) / (nombre total d'exigences)
# - Chaque exigence a un poids égal

# 📋 STRUCTURE DE RÉPONSE OBLIGATOIRE :

# {{
#   "compliance_score": 0.85,
#   "compliance_rows": [
#     {{
#       "requirement_id": "REQ-001",
#       "requirement_text": "24 ports Gigabit Ethernet",
#       "specified_value": "24 ports",
#       "product_response": "24 x 10/100/1000 Mbps + 4 x SFP",
#       "status": "CONFORME",
#       "score": 1.0,
#       "remarks": "Le produit a 24 ports Gigabit Ethernet"
#     }},
#     {{
#       "requirement_id": "REQ-002",
#       "requirement_text": "Support VLAN 802.1Q",
#       "specified_value": "802.1Q VLAN",
#       "product_response": "802.1Q, jusqu'à 4094 VLAN",
#       "status": "CONFORME",
#       "score": 1.0,
#       "remarks": "Support VLAN conforme à la norme 802.1Q"
#     }}
#   ],
#   "strengths": [
#     "24 ports Gigabit Ethernet",
#     "PoE+ 195W",
#     "VLAN 802.1Q",
#     "SNMP v3"
#   ],
#   "gaps": [
#     "Pas de stacking",
#     "Pas de modules SFP+"
#   ]
# }}

# 🎯 POUR CHAQUE PRODUIT, IDENTIFIE :
# 1. Les exigences CONFORME → Points forts
# 2. Les exigences PARTIEL → Points d'attention
# 3. Les exigences NON_CONFORME → Incompatibilités

# 📌 CONSIGNES SPÉCIFIQUES PAR TYPE DE PRODUIT :

# **Commutateurs (switches)** : Évalue sur :
# - Ports (nombre, type, débit)
# - PoE (présence, budget, standard)
# - VLAN (802.1Q, nombre)
# - Management (SNMP, Web, CLI)
# - Sécurité (802.1X, ACL)
# - Redondance (alimentation, stacking)
# - Montage (rack, format)

# **Caméras** : Évalue sur :
# - Résolution (MP, qualité)
# - Type (dôme, bullet, PTZ)
# - Vision nocturne (IR, distance)
# - Alimentation (PoE, 12V)
# - Protection (IP, IK)
# - Compression (H.265, H.264)
# - Température de fonctionnement

# **Onduleurs (UPS)** : Évalue sur :
# - Puissance (VA, W)
# - Autonomie (minutes)
# - Type d'onde (sinusoïdale)
# - Gestion (SNMP, USB)
# - Format (rack, tour)
# - Connectique (prises)

# 💡 RÈGLES IMPORTANTES :
# - La réponse produit doit être EXTRAITE des spécifications du produit
# - Les remarques doivent être PRÉCISES et JUSTIFIÉES
# - Un produit peut être CONFORME pour le réseau mais NON_CONFORME pour la vidéo
# - Sois OBJECTIF et FACTUEL

# Génère le JSON MAINTENANT :
# """,
#     ),
#     (
#         "human",
#         """
# 📋 EXIGENCES TECHNIQUES À ÉVALUER :

# {requirements_json}

# 📦 PRODUIT À ÉVALUER (SPÉCIFICATIONS COMPLÈTES) :

# {product_info}

# 📚 CONTEXTE RAG (documents pertinents) :

# {context}

# ⚠️ RAPPEL : Pour chaque exigence, utilise la SPÉCIFICATION EXACTE du produit.
# NE RÉPONDS PAS AVEC LA MÊME VALEUR POUR TOUTES LES EXIGENCES.

# ➡️ ÉVALUE LA CONFORMITÉ DU PRODUIT PAR RAPPORT AUX EXIGENCES EN JSON COMPLET :
# """,
#     ),
# ])

MATCH_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Tu es un ingénieur avant-vente expert en conformité technique, spécialisé dans l'évaluation de produits ICT/ELV.

⚠️ RÈGLE ABSOLUE : Le produit a une catégorie spécifique. Seules les exigences PERTINENTES pour cette catégorie sont évaluées.

**EXEMPLES CONCRETS :**

📌 Exemple 1 : PRODUIT = CAMERA (catégorie: camera)
Exigence : "24 ports Gigabit Ethernet" → Statut : NON_APPLICABLE (une caméra n'a pas de ports)
Exigence : "Résolution 4 MP" → Statut : CONFORME
Exigence : "Vision nocturne IR" → Statut : CONFORME

📌 Exemple 2 : PRODUIT = SWITCH (catégorie: switch)
Exigence : "24 ports Gigabit Ethernet" → Statut : CONFORME
Exigence : "Vision nocturne IR" → Statut : NON_APPLICABLE (un switch n'a pas de vision nocturne)
Exigence : "VLAN 802.1Q" → Statut : CONFORME

📌 Exemple 3 : PRODUIT = UPS (catégorie: ups)
Exigence : "Autonomie 10 minutes" → Statut : CONFORME
Exigence : "24 ports Gigabit Ethernet" → Statut : NON_APPLICABLE
Exigence : "Onde sinusoïdale pure" → Statut : CONFORME

📊 STATUTS POSSIBLES :
- CONFORME (score: 1.0) : Le produit répond EXACTEMENT à l'exigence
- PARTIEL (score: 0.5) : Le produit répond PARTIELLEMENT
- NON_CONFORME (score: 0.0) : Le produit NE répond PAS
- NON_APPLICABLE (score: 0.0) : L'exigence ne concerne PAS ce type de produit

📊 CALCUL DU SCORE GLOBAL :
- Score = MOYENNE des scores des exigences APPLICABLES uniquement
- Les exigences NON_APPLICABLE sont EXCLUES du calcul
- Exemple : 8 exigences, 2 applicables (1 CONFORME + 1 PARTIEL) → Score = (1.0 + 0.5) / 2 = 0.75

📋 STRUCTURE JSON OBLIGATOIRE :

{{
  "compliance_score": 0.75,
  "compliance_rows": [
    {{
      "requirement_id": "REQ-001",
      "requirement_text": "24 ports Gigabit Ethernet",
      "specified_value": "24 ports",
      "product_response": "24 x 10/100/1000 Mbps + 4 x SFP",
      "status": "CONFORME",
      "score": 1.0,
      "remarks": "Le produit a 24 ports Gigabit Ethernet"
    }},
    {{
      "requirement_id": "REQ-002",
      "requirement_text": "Vision nocturne IR",
      "specified_value": "IR 30m",
      "product_response": "Non applicable",
      "status": "NON_APPLICABLE",
      "score": 0.0,
      "remarks": "Ce produit est un switch, pas une caméra"
    }}
  ],
  "strengths": [
    "24 ports Gigabit Ethernet",
    "PoE+ 195W"
  ],
  "gaps": [
    "Pas de stacking"
  ]
}}

🎯 RÈGLES D'OR :
1. Pour CHAQUE exigence, détermine si elle est APPLICABLE à la catégorie du produit
2. Si APPLICABLE : compare avec les spécifications du produit
3. Si NON APPLICABLE : status = "NON_APPLICABLE", score = 0.0
4. La réponse produit doit être la SPÉCIFICATION EXACTE du produit
5. Chaque exigence doit avoir une réponse UNIQUE

Génère le JSON MAINTENANT :
""",
    ),
    (
        "human",
        """
📋 EXIGENCES TECHNIQUES À ÉVALUER :

{requirements_json}

📦 PRODUIT À ÉVALUER (SPÉCIFICATIONS COMPLÈTES) :

{product_info}

📚 CONTEXTE RAG :

{context}

⚠️ RAPPEL : Le produit est de catégorie "{category}".
Évalue UNIQUEMENT les exigences PERTINENTES pour cette catégorie.
Marque les autres comme "NON_APPLICABLE".
Le score est la MOYENNE des exigences applicables uniquement.

➡️ ÉVALUE LA CONFORMITÉ EN JSON COMPLET :
""",
    ),
])

def match_product_compliance(
    requirements: List[Dict[str, Any]],
    product: Dict[str, Any],
    context_docs: List[Any],
) -> Dict[str, Any]:
    """
    Matches a product against requirements and returns compliance scores.
    """
    logger.info(f"Matching produit: {product.get('reference', 'unknown')}")
    
    # Préparer le contexte
    context_text = ""
    if context_docs:
        for doc in context_docs:
            if isinstance(doc, dict):
                content = doc.get("content", "")
            else:
                content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            if content:
                context_text += f"\n---\n{content}\n"
    
    # Préparer le product_info structuré
    specs = product.get("specs", {})
    specs_lines = []
    for key, value in specs.items():
        if value and value != "":
            key_clean = key.replace('_', ' ').capitalize()
            specs_lines.append(f"  - {key_clean}: {value}")
    
    specs_text = "\n".join(specs_lines) if specs_lines else "  - Aucune spécification disponible"
    
    # ✅ RÉCUPÉRER LA CATÉGORIE
    category = product.get("category", "network_device")
    
    product_info = (
        f"Nom : {product.get('name', 'Inconnu')}\n"
        f"Fabricant : {product.get('manufacturer', 'Inconnu')}\n"
        f"Référence : {product.get('reference', 'Inconnu')}\n"
        f"Catégorie : {category}\n"
        f"\n📋 SPÉCIFICATIONS TECHNIQUES :\n{specs_text}"
    )
    
    logger.info(f"📦 Product info envoyé au LLM:\n{product_info}")
    logger.info(f"📋 Catégorie: {category}")
    
    # Appeler le LLM avec la catégorie
    llm = get_llm(temperature=0.0)
    chain = MATCH_PROMPT | llm | StrOutputParser()

    try:
        raw = chain.invoke({
            "requirements_json": json.dumps(
                requirements,
                ensure_ascii=False,
                indent=2,
            ),
            "product_info": product_info,
            "context": context_text,
            "category": category,  # ✅ TRANSMETTRE LA CATÉGORIE
        })
        
        # Log de la réponse brute
        logger.info("=" * 60)
        logger.info("📝 RÉPONSE BRUTE DU LLM (match_product_compliance):")
        logger.info("=" * 60)
        logger.info(raw[:500] + "..." if len(raw) > 500 else raw)
        logger.info("=" * 60)
        logger.info(f"📊 Longueur: {len(raw)} caractères")
        
        # Parser le JSON
        result = clean_json_response(raw)

        # ✅ AJOUTER CETTE CORRECTION ICI
        # ============================================================
        # VÉRIFIER SI DES EXIGENCES SONT APPLICABLES
        # ============================================================
        compliance_rows = result.get('compliance_rows', [])
        applicable_rows = [r for r in compliance_rows if r.get('status') != 'NON_APPLICABLE']
        
        if not applicable_rows:
            # ✅ AUCUNE EXIGENCE APPLICABLE → SCORE = 0%
            logger.info(f"⚠️ Aucune exigence applicable pour {product.get('name')}")
            result["compliance_score"] = 0.0
            result["strengths"] = ["Produit disponible dans le catalogue"]
            result["gaps"] = ["Aucune exigence ne correspond à ce type de produit"]
        else:
            # ✅ RECALCULER LE SCORE SI BESOIN
            total_score = sum(r.get('score', 0) for r in applicable_rows)
            result["compliance_score"] = total_score / len(applicable_rows)
            logger.info(f"✅ Score recalculé: {result['compliance_score']} ({len(applicable_rows)} exigences applicables)")
        
        # ✅ AJOUTER LES INFOS PRODUIT
        result["product_id"] = product.get("id") or product.get("product_id")
        result["product_name"] = product.get("name")
        result["manufacturer"] = product.get("manufacturer")
        result["reference"] = product.get("reference")
        
        # ✅ LOG DU RÉSULTAT PARSÉ
        logger.info(f"✅ Score final: {result.get('compliance_score', 'N/A')}")
        
        # Compter les statuts
        rows = result.get('compliance_rows', [])
        applicable = [r for r in rows if r.get('status') != 'NON_APPLICABLE']
        conformes = [r for r in applicable if r.get('status') == 'CONFORME']
        
        logger.info(f"📊 Exigences: {len(rows)} total, {len(applicable)} applicables, {len(conformes)} conformes")
        
        for row in rows[:5]:
            logger.info(f"   {row.get('requirement_id')}: {row.get('status')} → {row.get('product_response', 'N/A')[:50]}")
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors du matching: {e}")
        raise

# ============================================================
# 3. OFFER GENERATION
# ============================================================

OFFER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Tu es un ingénieur avant-vente senior spécialisé ICT, ELV et Télécom.

Génère une offre technique professionnelle, complète et personnalisée.

⚠️ RÈGLES :
1. Réponds UNIQUEMENT en JSON
2. L'offre doit être ADAPTÉE au projet (pas générique)
3. Justifie chaque choix technique avec des arguments précis
4. Utilise le CONTEXTE RAG pour enrichir l'offre
5. Le BOQ est estimatif (quantités seulement, sans prix unitaire)

📋 STRUCTURE OBLIGATOIRE :

{{
  "title": "Offre Technique - [Nom du Projet]",
  "reference": "REF-XXXXX",
  "sections": [
    {{
      "title": "1. Introduction",
      "content": "Présentation de la société, contexte du projet, objectifs..."
    }},
    {{
      "title": "2. Compréhension du Besoin",
      "content": "Analyse détaillée des besoins du client, exigences clés..."
    }},
    {{
      "title": "3. Synthèse des Exigences Techniques",
      "content": "Liste structurée des exigences techniques identifiées..."
    }},
    {{
      "title": "4. Solution Technique Proposée",
      "content": "Description de la solution, architecture, composants..."
    }},
    {{
      "title": "5. Équipements et Matériels",
      "content": "Détail des équipements proposés avec justifications..."
    }},
    {{
      "title": "6. Réseau, Câblage et Topologie ELV",
      "content": "Description de l'architecture réseau, câblage, topologie..."
    }},
    {{
      "title": "7. Méthodologie d'Exécution",
      "content": "Planning, phases d'installation, tests et recettes..."
    }},
    {{
      "title": "8. Tableau de Conformité",
      "content": "Tableau détaillé de conformité (exigence → réponse → statut)"
    }}
  ],
  "boq": [
    {{
      "pos": "1",
      "designation": "Désignation du produit",
      "reference": "Réf. constructeur",
      "manufacturer": "Fabricant",
      "unit": "U",
      "quantity": 1,
      "remarks": "Commentaire"
    }}
  ],
  "compliance_table": [
    {{
      "requirement_id": "REQ-001",
      "requirement_text": "Texte de l'exigence",
      "product_response": "Réponse du produit",
      "status": "CONFORME|PARTIEL|NON_CONFORME",
      "remarks": "Justification"
    }}
  ]
}}

📌 CONSIGNES SPÉCIFIQUES :
- L'introduction doit être personnalisée avec les informations du projet
- La solution technique doit justifier chaque choix
- Le BOQ est estimatif (quantités uniquement, PAS de prix)
- Le tableau de conformité doit lister chaque exigence avec son statut
- Utilise le CONTEXTE RAG pour enrichir l'offre

Génère l'offre COMPLÈTE maintenant :
""",
    ),
    (
        "human",
        """
📋 RÉSUMÉ DU BESOIN :

{summary}

🔒 CONTRAINTES CLÉS :

{constraints}

📦 PRODUITS SÉLECTIONNÉS :

{products_json}

📊 TAUX DE CONFORMITÉ :

{compliance_rate} %

📚 CONTEXTE RAG (documents pertinents) :

{context}

➡️ GÉNÈRE L'OFFRE TECHNIQUE COMPLÈTE EN JSON :
""",
    ),
])


# backend/services/llm_service.py

def generate_offer(
    summary: str,
    constraints: List[str],
    products: List[Dict[str, Any]],
    compliance_rate: float,
    requirements: List[Dict] = None,  # ✅ AJOUTER
    context_docs: List[Dict] = None   # ✅ AJOUTER
) -> Dict[str, Any]:
    """
    Generates a complete technical offer with RAG context and compliance table.
    """
    logger.info("Génération de l'offre technique")
    
    # Préparer les données
    products_text = json.dumps(products[:5], ensure_ascii=False, indent=2)[:3000]
    constraints_text = "\n".join(f"- {c}" for c in constraints[:10])
    
    # ✅ PRÉPARER LE CONTEXTE RAG
    context_text = ""
    if context_docs:
        context_text = "Documents techniques pertinents :\n"
        for doc in context_docs:
            content = doc.get("content", "")
            if content:
                context_text += f"\n---\n{content}\n"
    
    # ✅ PRÉPARER LES EXIGENCES POUR LE TABLEAU DE CONFORMITÉ
    requirements_text = ""
    if requirements:
        requirements_text = "\n".join([
            f"- {r.get('id')}: {r.get('description', '')[:100]}"
            for r in requirements[:10]
        ])
    
    llm = get_llm(temperature=0.3)
    chain = OFFER_PROMPT | llm | StrOutputParser()

    try:
        raw = chain.invoke({
            "summary": summary[:500],
            "constraints": constraints_text,
            "products_json": products_text,
            "compliance_rate": round(compliance_rate * 100, 1),
            "context": context_text,
            "requirements": requirements_text  # ✅ AJOUTER
        })
        
        logger.info(f"Réponse offre reçue: {len(raw)} caractères")
        result = clean_json_response(raw)
        
        # ✅ AJOUTER LE TABLEAU DE CONFORMITÉ SI ABSENT
        if not result.get("compliance_table") and requirements:
            result["compliance_table"] = [
                {
                    "requirement_id": req.get("id"),
                    "requirement_text": req.get("description", ""),
                    "product_response": "Voir les produits sélectionnés",
                    "status": "À vérifier",
                    "remarks": "Vérifier la conformité avec les produits proposés"
                }
                for req in requirements[:8]
            ]
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'offre: {e}")
        raise


def detect_incompatibilities(requirements: list, product: dict, match_result: dict) -> list:
    """
    Détecte les incompatibilités entre le produit et les exigences
    """
    incompatibilities = []
    
    compliance_rows = match_result.get("compliance_rows", [])
    
    for row in compliance_rows:
        if row.get("status") == "NON_CONFORME":
            incompatibilities.append({
                "requirement_id": row.get("requirement_id"),
                "requirement_text": row.get("requirement_text"),
                "specified_value": row.get("specified_value"),
                "product_response": row.get("product_response"),
                "remarks": row.get("remarks", "Le produit ne répond pas à cette exigence"),
                "severity": "critique"  # ou "majeure" / "mineure"
            })
    
    return incompatibilities

def suggest_alternatives(
    requirements: list,
    current_product: dict,
    all_products: list,
    match_result: dict
) -> list:
    """
    Suggère des produits alternatifs pour les exigences non conformes
    """
    alternatives = []
    
    # Récupérer les exigences non conformes
    compliance_rows = match_result.get("compliance_rows", [])
    non_conform_rows = [r for r in compliance_rows if r.get("status") == "NON_CONFORME"]
    
    if not non_conform_rows:
        return alternatives
    
    # Pour chaque produit alternatif
    for product in all_products:
        if product.get("id") == current_product.get("id"):
            continue  # Ignorer le produit actuel
        
        # Vérifier si ce produit répond aux exigences non conformes
        try:
            alt_result = match_product_compliance(
                requirements=non_conform_rows,
                product=product,
                context_docs=[]
            )
            
            alt_score = alt_result.get("compliance_score", 0)
            
            # Si le score est bon, suggérer comme alternative
            if alt_score >= 0.7:
                alternatives.append({
                    "product_id": product.get("id"),
                    "product_name": product.get("name"),
                    "manufacturer": product.get("manufacturer"),
                    "reference": product.get("reference"),
                    "compliance_score": alt_score,
                    "addressed_requirements": [
                        r.get("requirement_id") for r in alt_result.get("compliance_rows", [])
                        if r.get("status") == "CONFORME"
                    ],
                    "why": f"Ce produit répond à {len([r for r in alt_result.get('compliance_rows', []) if r.get('status') == 'CONFORME'])} exigences non conformes"
                })
        except Exception as e:
            logger.warning(f"Erreur d'alternative pour {product.get('name')}: {e}")
    
    # Trier par score
    alternatives.sort(key=lambda x: x.get("compliance_score", 0), reverse=True)
    
    return alternatives[:3]  # Top 3 alternatives