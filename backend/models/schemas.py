from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ConformityStatus(str, Enum):
    CONFORME = "CONFORME"
    PARTIEL = "PARTIEL"
    NON_CONFORME = "NON_CONFORME"
    NON_VERIFIE = "NON_VERIFIE"


class Requirement(BaseModel):
    id: str
    section: str
    description: str
    value: Optional[str] = None


class ComplianceRow(BaseModel):
    requirement_id: str
    requirement_text: str
    specified_value: Optional[str]
    product_response: str
    status: ConformityStatus
    remarks: Optional[str] = None


class ProductMatch(BaseModel):
    product_id: str
    product_name: str
    manufacturer: str
    reference: str
    compliance_score: float = Field(ge=0, le=1)
    compliance_rows: list[ComplianceRow]
    strengths: list[str]
    gaps: list[str]


class AnalysisResult(BaseModel):
    document_name: str
    extracted_requirements: list[Requirement]
    summary: str
    key_constraints: list[str]
    recommended_products: list[ProductMatch]


class OfferSection(BaseModel):
    title: str
    content: str


class GeneratedOffer(BaseModel):
    title: str
    reference: str
    sections: list[OfferSection]
    boq: list[dict]
    compliance_table: list[ComplianceRow]
    total_compliance_rate: float
