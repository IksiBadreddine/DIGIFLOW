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
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider != "ollama":
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return ChatOllama(
        model=os.getenv("LLM_MODEL", "qwen2.5:7b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=temperature,
        num_predict=8192,     # ✅ Maximum tokens à générer (pour les longs CDC)
        num_ctx=16384,        # ✅ Contexte de 16K tokens
        repeat_penalty=1.1,   # ✅ Évite les répétitions
        top_k=40,            # ✅ Qualité de génération
        top_p=0.9,           # ✅ Qualité de génération
    )


# ============================================================
# JSON Helper - Version robuste
# ============================================================

def clean_json_response(raw: str) -> dict:
    """
    Extract and parse JSON returned by the LLM.
    Handles incomplete JSON by attempting to complete it.
    """
    # Nettoyer les espaces invisibles
    raw = raw.strip()
    raw = raw.replace('\u200b', '')
    raw = raw.replace('\ufeff', '')
    
    # Supprimer les marqueurs markdown
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    
    # Supprimer les préfixes
    raw = re.sub(r'^(?:assistant|json)\s*', '', raw, flags=re.IGNORECASE)
    
    # Trouver le premier { et le dernier }
    start = raw.find("{")
    end = raw.rfind("}")
    
    if start == -1 or end == -1:
        raise ValueError(f"LLM did not return JSON.\n\nResponse:\n{raw[:500]}...")
    
    # Extraire la partie JSON
    json_str = raw[start:end + 1]
    
    # ✅ FIX : Si le JSON est incomplet, on essaie de le compléter
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    
    if open_braces > close_braces:
        logger.warning(f"JSON incomplet : {open_braces} ouvertures, {close_braces} fermetures")
        # Ajouter les accolades manquantes
        json_str += '}' * (open_braces - close_braces)
        logger.info(f"JSON complété avec {open_braces - close_braces} accolades")
    
    # Supprimer les caractères de contrôle
    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
    
    # Tentative de parsing
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Erreur JSON initiale: {e}")
        
        # Nettoyage avancé
        try:
            # Remplacer les guillemets simples
            json_fixed = re.sub(r"'([^']+)'", r'"\1"', json_str)
            
            # Supprimer les virgules en trop
            json_fixed = re.sub(r',\s*}', '}', json_fixed)
            json_fixed = re.sub(r',\s*]', ']', json_fixed)
            
            # Supprimer les sauts de ligne dans les chaînes
            json_fixed = re.sub(r'\n(?=[^"]*")', ' ', json_fixed)
            
            # Supprimer les espaces avant les deux-points
            json_fixed = re.sub(r'\s+:\s*', ':', json_fixed)
            
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

MATCH_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Tu es un ingénieur réseaux expert en conformité technique.

Compare les exigences avec les caractéristiques du produit.

⚠️ RÈGLES STRICTES :
1. Réponds UNIQUEMENT en JSON
2. Le JSON doit être COMPLET
3. Sois PRÉCIS dans l'évaluation

Structure obligatoire :

{{
  "compliance_score": 0.95,
  "compliance_rows": [
    {{
      "requirement_id": "REQ-001",
      "requirement_text": "Texte de l'exigence",
      "specified_value": "Valeur spécifiée",
      "product_response": "Ce que le produit offre",
      "status": "CONFORME|PARTIEL|NON_CONFORME",
      "remarks": "Commentaire"
    }}
  ],
  "strengths": [
    "Point fort 1",
    "Point fort 2"
  ],
  "gaps": [
    "Écart 1",
    "Écart 2"
  ]
}}

Génère le JSON MAINTENANT :
""",
    ),
    (
        "human",
        """
EXIGENCES TECHNIQUES :

{requirements_json}

PRODUIT À ÉVALUER :

{product_info}

CONTEXTE EXTRAIT DU CDC :

{context}

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
    context_text = "\n\n---\n\n".join(
        doc.page_content[:500]  # Limiter chaque contexte
        for doc in context_docs[:3]
    )
    
    product_info = (
        f"Fabricant : {product['manufacturer']}\n"
        f"Référence : {product['reference']}\n"
        f"Catégorie : {product.get('category', 'N/A')}\n"
        f"Description : {product['datasheet_summary'][:500]}\n"
        f"Spécifications : {json.dumps(product['specs'], ensure_ascii=False, indent=2)}"
    )
    
    llm = get_llm(temperature=0.0)
    chain = MATCH_PROMPT | llm | StrOutputParser()

    try:
        raw = chain.invoke({
            "requirements_json": json.dumps(
                requirements[:15],  # ✅ Limiter à 15 exigences pour éviter la surcharge
                ensure_ascii=False,
                indent=2,
            ),
            "product_info": product_info[:3000],  # ✅ Limiter
            "context": context_text[:2000],  # ✅ Limiter
        })
        
        logger.info(f"Réponse match reçue: {len(raw)} caractères")
        return clean_json_response(raw)
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

Génère une offre technique professionnelle et complète.

⚠️ RÈGLES :
1. Réponds UNIQUEMENT en JSON
2. Offre structurée et professionnelle
3. Justifie chaque choix technique

Structure JSON obligatoire :

{{
  "title": "Offre Technique - Nom du Projet",
  "reference": "REF-XXXXX",
  "sections": [
    {{
      "title": "1. Introduction",
      "content": "Texte complet de l'introduction..."
    }},
    {{
      "title": "2. Compréhension du Besoin",
      "content": "Analyse détaillée du besoin..."
    }},
    {{
      "title": "3. Solution Technique",
      "content": "Description de la solution..."
    }},
    {{
      "title": "4. Équipements Proposés",
      "content": "Détail des équipements..."
    }},
    {{
      "title": "5. Architecture",
      "content": "Description de l'architecture..."
    }},
    {{
      "title": "6. Justification des Choix",
      "content": "Justification technique..."
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
      "unit_price_eur": 0,
      "remarks": "Commentaire"
    }}
  ]
}}

Génère l'offre COMPLÈTE maintenant :
""",
    ),
    (
        "human",
        """
RÉSUMÉ DU BESOIN :

{summary}

CONTRAINTES CLÉS :

{constraints}

PRODUITS SÉLECTIONNÉS :

{products_json}

TAUX DE CONFORMITÉ :

{compliance_rate} %

➡️ GÉNÈRE L'OFFRE TECHNIQUE COMPLÈTE EN JSON :
""",
    ),
])


def generate_offer(
    summary: str,
    constraints: List[str],
    products: List[Dict[str, Any]],
    compliance_rate: float,
) -> Dict[str, Any]:
    """
    Generates a complete technical offer.
    """
    logger.info("Génération de l'offre technique")
    
    # Préparer les données
    products_text = json.dumps(products[:5], ensure_ascii=False, indent=2)[:3000]
    constraints_text = "\n".join(f"- {c}" for c in constraints[:10])
    
    llm = get_llm(temperature=0.3)
    chain = OFFER_PROMPT | llm | StrOutputParser()

    try:
        raw = chain.invoke({
            "summary": summary[:500],
            "constraints": constraints_text,
            "products_json": products_text,
            "compliance_rate": round(compliance_rate * 100, 1),
        })
        
        logger.info(f"Réponse offre reçue: {len(raw)} caractères")
        return clean_json_response(raw)
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'offre: {e}")
        raise