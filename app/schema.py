"""Data models for the chemical supplier agent."""
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class SupplierHit(BaseModel):
    """A single supplier result with evidence."""
    supplier_name: str
    website: HttpUrl
    contact_email: Optional[str] = None
    email_status: Optional[str] = None  # valid/accept-all/unknown
    evidence_url: HttpUrl
    confidence_score: float = Field(ge=0, le=10)
    country: Optional[str] = None


class AgentResult(BaseModel):
    """Complete result from the chemical supplier agent."""
    chemical_name: str
    cas: str
    suppliers: list[SupplierHit]
