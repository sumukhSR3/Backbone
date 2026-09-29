"""
Principal Diagnosis Review API Handler.
Decoupled component that retrieves resources over HTTP FHIR endpoints and returns ICD-10-CM recommendations.
"""

from typing import Dict, Any
from app.schemas import ReviewRequest
from app.services.review_engine import PrincipalDiagnosisReviewEngine


def handle_review(data: Dict[str, Any]) -> Dict[str, Any]:
    req = ReviewRequest.from_dict(data)
    if not req.encounter_id:
        raise ValueError("encounter_id is required for principal diagnosis review")
    if not req.fhir_api_base_url:
        raise ValueError("fhir_api_base_url is required for principal diagnosis review")

    result = PrincipalDiagnosisReviewEngine.evaluate_encounter(req)
    return result.to_dict()
