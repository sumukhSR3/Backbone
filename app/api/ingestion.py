"""
Ingestion API Endpoint.
Accepts clinical notes, extracts facts, maps to FHIR R4, and persists idempotently.
"""

from typing import Dict, Any
from app.schemas import IngestionRequest, IngestionResult
from app.services.extractor import ClinicalFactExtractor
from app.services.fhir_mapper import FHIRR4Mapper
from app.services.storage import StorageService


def handle_ingestion(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingestion workflow controller.
    """
    request = IngestionRequest.from_dict(data)

    if not request.note_text:
        raise ValueError("note_text is required for ingestion")
    if not request.encounter_id:
        raise ValueError("encounter_id is required for ingestion")
    if not request.patient_id:
        raise ValueError("patient_id is required for ingestion")
    if not request.note_id:
        raise ValueError("note_id is required for ingestion")

    # 1. Deterministic Clinical Fact Extraction
    facts = ClinicalFactExtractor.extract_facts(request.note_text, request.note_id)

    # 2. Map to FHIR R4 Bundle & Validate
    bundle = FHIRR4Mapper.build_fhir_bundle(request, facts)

    # 3. Idempotent Storage Persistence
    result = StorageService.ingest_note(request, facts, bundle)

    return result.to_dict()
