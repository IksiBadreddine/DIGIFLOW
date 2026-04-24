"""
LLM Analysis Service
GPT-4 chains for:
  1. Requirement extraction from CdC
  2. Product compliance matching
  3. Offer generation
"""
import os
import json
import re
from typing import Optional

from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from models.schemas import (
    Requirement, ComplianceRow, ConformityStatus,
    ProductMatch, AnalysisResult, GeneratedOffer, OfferSection
)


def get_llm(temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=temperature,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


# ─────────────────────────────────────────────
# 1. REQUIREMENT EXTRACTION
# ─────────────────────────────────────────────

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un ingénieur avant-vente expert en réseaux, télécoms et sécurité (ICT/ELV).
Analyse le cahier des charges suivant et extrais TOUTES les exigences techniques.

Réponds UNIQUEMENT en JSON valide avec cette structure :
{{
  "summary": "Résumé en 3-4 phrases du besoin client",
  "key_constraints": ["contrainte1", "contrainte2", ...],
  "requirements": [
    {{
      "id": "REQ-001",
      "section": "Nom de section (ex: Switch d'accès, Sécurité, etc.)",
      "description": "Description de l'exigence",
      "value": "Valeur spécifiée si applicable (ex: 24 ports, 88 Gbps, etc.)"
    }}
  ]
}}

Sois exhaustif. Inclus : ports, débits, protocoles, standards IEEE, sécurité, gestion, environnement, alimentation."""),
    ("human", "CAHIER DES CHARGES:\n\n{cdc_text}")
])


def extract_requirements(cdc_text: str) -> dict:
    llm = get_llm(temperature=0.0)
    chain = EXTRACT_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({"cdc_text": cdc_text[:12000]})  # token guard
    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ─────────────────────────────────────────────
# 2. PRODUCT COMPLIANCE MATCHING
# ─────────────────────────────────────────────

MATCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un ingénieur réseaux expert en conformité technique.
Compare les exigences du cahier des charges avec les spécifications du produit.

Réponds UNIQUEMENT en JSON valide :
{{
  "compliance_score": 0.95,
  "compliance_rows": [
    {{
      "requirement_id": "REQ-001",
      "requirement_text": "texte de l'exigence",
      "specified_value": "valeur requise ou null",
      "product_response": "ce que le produit offre exactement",
      "status": "CONFORME|PARTIEL|NON_CONFORME",
      "remarks": "remarque optionnelle"
    }}
  ],
  "strengths": ["point fort 1", "point fort 2"],
  "gaps": ["écart 1 si existant"]
}}

Règles de conformité :
- CONFORME : le produit satisfait ou dépasse l'exigence
- PARTIEL : satisfait partiellement ou avec réserve mineure
- NON_CONFORME : ne satisfait pas l'exigence"""),
    ("human", """EXIGENCES DU CAHIER DES CHARGES:
{requirements_json}

FICHE PRODUIT:
{product_info}

CONTEXTE ADDITIONNEL (base documentaire):
{context}""")
])


def match_product_compliance(
    requirements: list[dict],
    product: dict,
    context_docs: list,
) -> dict:
    llm = get_llm(temperature=0.0)
    chain = MATCH_PROMPT | llm | StrOutputParser()

    context_text = "\n\n---\n\n".join([d.page_content for d in context_docs[:3]])
    product_info = (
        f"Fabricant: {product['manufacturer']}\n"
        f"Référence: {product['reference']}\n"
        f"Description: {product['datasheet_summary']}\n"
        f"Specs: {json.dumps(product['specs'], ensure_ascii=False)}"
    )

    raw = chain.invoke({
        "requirements_json": json.dumps(requirements[:20], ensure_ascii=False, indent=2),
        "product_info": product_info,
        "context": context_text[:3000],
    })
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ─────────────────────────────────────────────
# 3. OFFER GENERATION
# ─────────────────────────────────────────────

OFFER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un ingénieur avant-vente senior spécialisé réseaux ICT/ELV/Télécom.
Génère une offre technique professionnelle complète en français.

Réponds UNIQUEMENT en JSON valide :
{{
  "title": "Titre de l'offre technique",
  "reference": "Référence document",
  "sections": [
    {{
      "title": "1. Introduction et Présentation",
      "content": "Texte complet de la section..."
    }},
    {{
      "title": "2. Compréhension du Besoin",
      "content": "..."
    }},
    {{
      "title": "3. Solution Technique Proposée",
      "content": "..."
    }},
    {{
      "title": "4. Description des Équipements",
      "content": "..."
    }},
    {{
      "title": "5. Architecture et Topologie Réseau",
      "content": "..."
    }},
    {{
      "title": "6. Justification des Choix Techniques",
      "content": "..."
    }}
  ],
  "boq": [
    {{
      "pos": "1",
      "designation": "Nom du produit",
      "reference": "Ref",
      "manufacturer": "Fabricant",
      "unit": "U",
      "quantity": 1,
      "unit_price_eur": 0,
      "remarks": "remarque"
    }}
  ]
}}

L'offre doit être professionnelle, détaillée et justifier techniquement chaque choix."""),
    ("human", """RÉSUMÉ DU BESOIN CLIENT:
{summary}

CONTRAINTES CLÉS:
{constraints}

PRODUITS RECOMMANDÉS:
{products_json}

TAUX DE CONFORMITÉ: {compliance_rate}%""")
])


def generate_offer(
    summary: str,
    constraints: list[str],
    products: list[dict],
    compliance_rate: float,
) -> dict:
    llm = get_llm(temperature=0.3)
    chain = OFFER_PROMPT | llm | StrOutputParser()

    raw = chain.invoke({
        "summary": summary,
        "constraints": "\n".join(f"- {c}" for c in constraints),
        "products_json": json.dumps(products, ensure_ascii=False, indent=2)[:4000],
        "compliance_rate": round(compliance_rate * 100, 1),
    })
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
