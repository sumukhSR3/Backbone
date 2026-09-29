"""
Pydantic and Data Structure Schemas for FHIR R4 & Clinical Note Ingestion.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class IngestionRequest:
    patient_id: str
    encounter_id: str
    note_id: str
    source_system: str
    note_text: str
    author: Optional[str] = "Dr. Clinical CDI"
    service: Optional[str] = "Internal Medicine"
    encounter_class: str = "IMP"
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "note_id": self.note_id,
            "source_system": self.source_system,
            "note_text": self.note_text,
            "author": self.author,
            "service": self.service,
            "encounter_class": self.encounter_class,
            "admission_date": self.admission_date,
            "discharge_date": self.discharge_date,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IngestionRequest":
        return cls(
            patient_id=str(data.get("patient_id", "")).strip(),
            encounter_id=str(data.get("encounter_id", "")).strip(),
            note_id=str(data.get("note_id", "")).strip(),
            source_system=str(data.get("source_system", "")).strip(),
            note_text=str(data.get("note_text", "")).strip(),
            author=data.get("author", "Dr. Clinical CDI"),
            service=data.get("service", "Internal Medicine"),
            encounter_class=data.get("encounter_class", "IMP"),
            admission_date=data.get("admission_date"),
            discharge_date=data.get("discharge_date"),
        )


@dataclass
class ExtractedFact:
    condition_id: str
    display_name: str
    icd10_code: str
    category: str = "encounter-diagnosis"  # encounter-diagnosis | problem-list-item | chief-complaint
    verification_status: str = "confirmed"  # confirmed | provisional | unconfirmed | refuted
    clinical_status: str = "active"  # active | resolved | inactive
    present_on_admission: str = "Y"  # Y=Yes, N=No, U=Unknown, W=Clinically undetermined
    is_negated: bool = False
    is_uncertain: bool = False
    uncertainty_qualifier: Optional[str] = None  # probable, possible, suspected, rule out, likely
    acuity: str = "unspecified"  # acute, chronic, acute-on-chronic, unspecified
    supporting_text: str = ""
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "display_name": self.display_name,
            "icd10_code": self.icd10_code,
            "category": self.category,
            "verification_status": self.verification_status,
            "clinical_status": self.clinical_status,
            "present_on_admission": self.present_on_admission,
            "is_negated": self.is_negated,
            "is_uncertain": self.is_uncertain,
            "uncertainty_qualifier": self.uncertainty_qualifier,
            "acuity": self.acuity,
            "supporting_text": self.supporting_text,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


@dataclass
class IngestionResult:
    status: str  # ingested | duplicate
    note_id: str
    encounter_id: str
    patient_id: str
    content_hash: str
    extracted_facts_count: int
    fhir_bundle: Dict[str, Any]
    created_at: str
    message: str = "Note successfully ingested and mapped to FHIR R4 Bundle"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "note_id": self.note_id,
            "encounter_id": self.encounter_id,
            "patient_id": self.patient_id,
            "content_hash": self.content_hash,
            "extracted_facts_count": self.extracted_facts_count,
            "fhir_bundle": self.fhir_bundle,
            "created_at": self.created_at,
            "message": self.message,
        }


@dataclass
class ReviewRequest:
    encounter_id: str
    fhir_api_base_url: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewRequest":
        return cls(
            encounter_id=str(data.get("encounter_id", "")).strip(),
            fhir_api_base_url=str(data.get("fhir_api_base_url", "")).strip().rstrip("/"),
        )


@dataclass
class CompetingPossibility:
    icd10_code: str
    display_name: str
    verification_status: str
    exclusion_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "icd10_code": self.icd10_code,
            "display_name": self.display_name,
            "verification_status": self.verification_status,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass
class ReviewResult:
    encounter_id: str
    recommendation_status: str  # SUPPORTED | CLARIFICATION_NEEDED | UNSUPPORTED
    recommended_condition: Optional[Dict[str, Any]] = None
    supporting_passages: List[str] = field(default_factory=list)
    guideline_references: List[str] = field(default_factory=list)
    competing_possibilities: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "recommendation_status": self.recommendation_status,
            "recommended_condition": self.recommended_condition,
            "supporting_passages": self.supporting_passages,
            "guideline_references": self.guideline_references,
            "competing_possibilities": self.competing_possibilities,
            "assumptions": self.assumptions,
            "missing_information": self.missing_information,
            "next_action": self.next_action,
        }
