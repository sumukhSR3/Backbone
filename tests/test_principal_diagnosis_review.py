"""
Unit & Rule Tests for FY 2026 ICD-10-CM Principal Diagnosis Review Component.
"""

import unittest
import threading
import time
from app.database import db
from app.api.ingestion import handle_ingestion
from app.server import APIRequestHandler, ReusableHTTPServer
from app.schemas import ReviewRequest
from app.services.review_engine import PrincipalDiagnosisReviewEngine


class TestPrincipalDiagnosisReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE note_id LIKE 'NOTE-REV%';")
            cursor.execute("DELETE FROM fhir_resources WHERE encounter_id LIKE 'ENC-REV%';")
            cursor.execute("DELETE FROM ingestion_logs WHERE note_id LIKE 'NOTE-REV%';")
            conn.commit()
        finally:
            conn.close()

        # Start a local HTTP server on port 8999 with socket reuse for strict HTTP testing
        cls.server = ReusableHTTPServer(("127.0.0.1", 8999), APIRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_sepsis_over_pneumonia_review(self):
        # Ingest Sepsis note
        payload = {
            "patient_id": "PAT-REV1",
            "encounter_id": "ENC-REV1",
            "note_id": "NOTE-REV1",
            "source_system": "EPIC_EMR",
            "note_text": "Patient admitted to ICU with severe sepsis due to community-acquired pneumonia. History of hypertension."
        }
        handle_ingestion(payload)

        # Run Principal Diagnosis Review strictly over HTTP
        req = ReviewRequest(encounter_id="ENC-REV1", fhir_api_base_url="http://127.0.0.1:8999")
        res = PrincipalDiagnosisReviewEngine.evaluate_encounter(req)

        self.assertEqual(res.recommendation_status, "SUPPORTED")
        self.assertIsNotNone(res.recommended_condition)
        self.assertEqual(res.recommended_condition["icd10_code"], "A41.9")  # Sepsis
        self.assertIn("FY 2026 ICD-10-CM Guidelines Section II.B", " ".join(res.guideline_references))

    def test_unconfirmed_contrasting_diagnoses_review(self):
        # Ingest unconfirmed appendicitis vs diverticulitis
        payload = {
            "patient_id": "PAT-REV2",
            "encounter_id": "ENC-REV2",
            "note_id": "NOTE-REV2",
            "source_system": "EPIC_EMR",
            "note_text": "Patient discharged with probable acute appendicitis vs suspected diverticulitis."
        }
        handle_ingestion(payload)

        req = ReviewRequest(encounter_id="ENC-REV2", fhir_api_base_url="http://127.0.0.1:8999")
        res = PrincipalDiagnosisReviewEngine.evaluate_encounter(req)

        self.assertEqual(res.recommendation_status, "CLARIFICATION_NEEDED")
        self.assertIn("FY 2026 ICD-10-CM Guidelines Section II.D", " ".join(res.guideline_references))
        self.assertIn("physician query", res.next_action.lower())


if __name__ == "__main__":
    unittest.main()
