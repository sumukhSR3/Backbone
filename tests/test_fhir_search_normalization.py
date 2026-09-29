"""
Unit Tests for FHIR Reference Search Normalization.
Verifies that searching by plain ID (e.g. ENC-9901) or FHIR reference (e.g. Encounter/ENC-9901) returns identical results.
"""

import unittest
from app.database import db
from app.schemas import IngestionRequest
from app.api.ingestion import handle_ingestion
from app.api.fhir import search_fhir_resources, get_fhir_resource
from app.services.storage import normalize_id


class TestFHIRSearchNormalization(unittest.TestCase):

    def setUp(self):
        db.init_db()
        payload = {
            "patient_id": "PAT-NORM1",
            "encounter_id": "ENC-NORM1",
            "note_id": "NOTE-NORM1",
            "source_system": "EPIC_EMR",
            "note_text": "Patient presented with severe sepsis due to pneumonia."
        }
        handle_ingestion(payload)

    def test_normalize_id_helper(self):
        self.assertEqual(normalize_id("ENC-9901"), "ENC-9901")
        self.assertEqual(normalize_id("Encounter/ENC-9901"), "ENC-9901")
        self.assertEqual(normalize_id("Patient/PAT-8801"), "PAT-8801")
        self.assertEqual(normalize_id("http://localhost:8000/fhir/Encounter/ENC-9901"), "ENC-9901")
        self.assertEqual(normalize_id("urn:uuid:ENC-9901"), "ENC-9901")

    def test_condition_search_with_plain_and_fhir_reference(self):
        # 1. Search with plain encounter ID
        plain_res = search_fhir_resources("Condition", encounter_id="ENC-NORM1")
        self.assertGreater(plain_res["total"], 0, "Plain encounter search returned 0 results")

        # 2. Search with FHIR reference 'Encounter/ENC-NORM1'
        ref_res = search_fhir_resources("Condition", encounter_id="Encounter/ENC-NORM1")
        self.assertGreater(ref_res["total"], 0, "FHIR reference search returned 0 results")

        # 3. Assert total counts match
        self.assertEqual(plain_res["total"], ref_res["total"])

        # 4. Search with full URL reference
        url_res = search_fhir_resources("Condition", encounter_id="http://localhost:8000/fhir/Encounter/ENC-NORM1")
        self.assertEqual(plain_res["total"], url_res["total"])

    def test_docref_search_with_plain_and_fhir_reference(self):
        plain_res = search_fhir_resources("DocumentReference", encounter_id="ENC-NORM1")
        self.assertEqual(plain_res["total"], 1)

        ref_res = search_fhir_resources("DocumentReference", encounter_id="Encounter/ENC-NORM1")
        self.assertEqual(ref_res["total"], 1)
        self.assertEqual(plain_res["total"], ref_res["total"])

    def test_get_resource_with_fhir_reference(self):
        plain_res = get_fhir_resource("Encounter", "ENC-NORM1")
        self.assertIsNotNone(plain_res)

        ref_res = get_fhir_resource("Encounter", "Encounter/ENC-NORM1")
        self.assertIsNotNone(ref_res)
        self.assertEqual(plain_res["id"], ref_res["id"])


if __name__ == "__main__":
    unittest.main()
