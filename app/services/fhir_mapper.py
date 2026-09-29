"""
FHIR R4 Resource Mapper and Schema Validator.
Converts extracted clinical facts and notes into compliant FHIR R4 resources and bundles.
"""

import base64
from typing import List, Dict, Any, Tuple
from app.schemas import IngestionRequest, ExtractedFact


class FHIRR4Mapper:
    """
    Transforms clinical ingestion payloads and extracted facts into an inspectable FHIR R4 Bundle.
    Performs structural and relational validation of resources.
    """

    @staticmethod
    def build_fhir_bundle(request: IngestionRequest, facts: List[ExtractedFact]) -> Dict[str, Any]:
        patient_id = request.patient_id
        encounter_id = request.encounter_id
        note_id = request.note_id

        # 1. Patient Resource
        patient_resource = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [
                {
                    "system": f"urn:oid:{request.source_system}.patients",
                    "value": patient_id,
                }
            ],
            "active": True,
            "gender": "unknown",
        }

        # 2. Encounter Resource
        encounter_resource = {
            "resourceType": "Encounter",
            "id": encounter_id,
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": request.encounter_class or "IMP",
                "display": "inpatient encounter",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "serviceType": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/service-type",
                        "display": request.service or "Internal Medicine",
                    }
                ]
            },
        }

        # 3. Condition Resources
        condition_resources = []
        for fact in facts:
            cond = {
                "resourceType": "Condition",
                "id": fact.condition_id,
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": fact.clinical_status,
                        }
                    ]
                },
                "verificationStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            "code": fact.verification_status,
                        }
                    ]
                },
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                "code": fact.category,
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": fact.icd10_code,
                            "display": fact.display_name,
                        }
                    ],
                    "text": fact.display_name,
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "encounter": {"reference": f"Encounter/{encounter_id}"},
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/condition-presentOnAdmission",
                        "valueCode": fact.present_on_admission,
                    },
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/condition-supportingText",
                        "valueString": fact.supporting_text,
                    },
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/condition-acuity",
                        "valueString": fact.acuity,
                    },
                ],
            }
            if fact.is_uncertain and fact.uncertainty_qualifier:
                cond["extension"].append(
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/condition-uncertaintyQualifier",
                        "valueString": fact.uncertainty_qualifier,
                    }
                )

            condition_resources.append(cond)

        # 4. Binary Resource (Original Note)
        encoded_note = base64.b64encode(request.note_text.encode("utf-8")).decode("utf-8")
        binary_id = f"BIN-{note_id}"
        binary_resource = {
            "resourceType": "Binary",
            "id": binary_id,
            "contentType": "text/plain",
            "data": encoded_note,
        }

        # 5. DocumentReference Resource
        docref_id = f"DOCREF-{note_id}"
        document_reference_resource = {
            "resourceType": "DocumentReference",
            "id": docref_id,
            "status": "current",
            "docStatus": "final",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "18842-5",
                        "display": "Discharge summary",
                    }
                ]
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "author": [{"display": request.author or "Attending Physician"}],
            "context": {"encounter": [{"reference": f"Encounter/{encounter_id}"}]},
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "url": f"Binary/{binary_id}",
                    }
                }
            ],
        }

        # Assemble Bundle
        resources = [patient_resource, encounter_resource] + condition_resources + [binary_resource, document_reference_resource]
        bundle_entries = []
        for r in resources:
            bundle_entries.append(
                {
                    "fullUrl": f"urn:uuid:{r['id']}",
                    "resource": r,
                }
            )

        bundle = {
            "resourceType": "Bundle",
            "id": f"BUNDLE-{encounter_id}",
            "type": "collection",
            "entry": bundle_entries,
        }

        # Validate bundle structure and relationships
        is_valid, errors = FHIRR4Mapper.validate_bundle(bundle)
        if not is_valid:
            raise ValueError(f"FHIR R4 Bundle validation failed: {', '.join(errors)}")

        return bundle

    @staticmethod
    def validate_bundle(bundle: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates FHIR resource schema completeness and reference integrity.
        """
        errors = []
        if bundle.get("resourceType") != "Bundle":
            errors.append("Invalid root resourceType, expected 'Bundle'")
            return False, errors

        entries = bundle.get("entry", [])
        resource_map = {}
        for entry in entries:
            res = entry.get("resource", {})
            rtype = res.get("resourceType")
            rid = res.get("id")
            if not rtype or not rid:
                errors.append("Bundle entry resource missing resourceType or id")
            else:
                resource_map[f"{rtype}/{rid}"] = res

        # Check references
        for key, res in resource_map.items():
            rtype = res.get("resourceType")

            if rtype == "Condition":
                patient_ref = res.get("subject", {}).get("reference")
                encounter_ref = res.get("encounter", {}).get("reference")
                if not patient_ref or patient_ref not in resource_map:
                    errors.append(f"Condition {res.get('id')} references missing Patient {patient_ref}")
                if not encounter_ref or encounter_ref not in resource_map:
                    errors.append(f"Condition {res.get('id')} references missing Encounter {encounter_ref}")

            elif rtype == "DocumentReference":
                patient_ref = res.get("subject", {}).get("reference")
                encounters = res.get("context", {}).get("encounter", [])
                enc_ref = encounters[0].get("reference") if encounters else None
                contents = res.get("content", [])
                binary_ref = contents[0].get("attachment", {}).get("url") if contents else None

                if not patient_ref or patient_ref not in resource_map:
                    errors.append(f"DocumentReference {res.get('id')} references missing Patient {patient_ref}")
                if not enc_ref or enc_ref not in resource_map:
                    errors.append(f"DocumentReference {res.get('id')} references missing Encounter {enc_ref}")
                if not binary_ref or binary_ref not in resource_map:
                    errors.append(f"DocumentReference {res.get('id')} references missing Binary {binary_ref}")

        return len(errors) == 0, errors
