"""
Unit Tests for FHIR R4 Bundle Construction & Schema Validation.
"""

import unittest
from app.schemas import IngestionRequest
from app.services.extractor import ClinicalFactExtractor
from app.services.fhir_mapper import FHIRR4Mapper


class TestFHIRMapper(unittest.TestCase):

    def test_bundle_creation_and_validation(self):
        req = IngestionRequest(
            patient_id="PAT-T1",
            encounter_id="ENC-T1",
            note_id="NOTE-T1",
            source_system="EPIC_EMR",
            note_text="Patient admitted with severe sepsis due to pneumonia."
        )
        facts = ClinicalFactExtractor.extract_facts(req.note_text, req.note_id)
        bundle = FHIRR4Mapper.build_fhir_bundle(req, facts)

        self.assertEqual(bundle["resourceType"], "Bundle")
        self.assertEqual(bundle["type"], "collection")

        resources = [entry["resource"] for entry in bundle["entry"]]
        rtypes = [r["resourceType"] for r in resources]

        self.assertIn("Patient", rtypes)
        self.assertIn("Encounter", rtypes)
        self.assertIn("Condition", rtypes)
        self.assertIn("DocumentReference", rtypes)
        self.assertIn("Binary", rtypes)

        # Validate schema & references
        is_valid, errors = FHIRR4Mapper.validate_bundle(bundle)
        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")


if __name__ == "__main__":
    unittest.main()
