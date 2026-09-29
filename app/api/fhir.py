"""
FHIR R4 REST API Handlers.
Exposes FHIR endpoints to retrieve individual resources and search by encounter/patient.
Normalizes FHIR references (e.g. Encounter/ENC-9901 -> ENC-9901).
"""

from typing import Dict, Any, List, Optional
from app.services.storage import StorageService, normalize_id


def get_fhir_resource(resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
    norm_id = normalize_id(resource_id)
    return StorageService.get_fhir_resource(resource_type, norm_id)


def search_fhir_resources(
    resource_type: str,
    encounter_id: Optional[str] = None,
    patient_id: Optional[str] = None
) -> Dict[str, Any]:
    norm_enc = normalize_id(encounter_id)
    norm_pat = normalize_id(patient_id)
    resources = StorageService.search_fhir_resources(resource_type, norm_enc, norm_pat)

    entries = []
    for r in resources:
        entries.append({
            "fullUrl": f"urn:uuid:{r.get('id')}",
            "resource": r
        })

    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": entries
    }
    return bundle
