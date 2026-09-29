"""
Verification Script for End-to-End Clinical Ingestion, FHIR, Review Engine, Normalization, and Tests.
"""

import sys
import os
import time
import threading
import unittest

sys.path.insert(0, ".")

from app.database import db
from app.schemas import IngestionRequest, ReviewRequest
from app.api.ingestion import handle_ingestion
from app.api.fhir import get_fhir_resource, search_fhir_resources
from app.api.review import handle_review
from app.api.metrics import get_metrics
from app.server import APIRequestHandler, ReusableHTTPServer
from app.services.review_engine import PrincipalDiagnosisReviewEngine

# Import test suites
from tests.test_extraction import TestClinicalFactExtractor
from tests.test_fhir_mapping import TestFHIRMapper
from tests.test_idempotency import TestIdempotency
from tests.test_principal_diagnosis_review import TestPrincipalDiagnosisReview
from tests.test_fhir_search_normalization import TestFHIRSearchNormalization


def verify_system():
    print("=" * 60)
    print("🏥 VERIFYING CLINICAL DATA & PRINCIPAL DIAGNOSIS REVIEW SYSTEM")
    print("=" * 60)

    # Step 1: Initialize Database
    print("\n[Step 1] Initializing Database Schema...")
    db.init_db()
    print("  ✅ Database initialized successfully.")

    # Step 2: Test Clinical Note Ingestion & FHIR Mapping
    print("\n[Step 2] Testing Clinical Note Ingestion & Fact Extraction...")
    note_payload = {
        "patient_id": "PAT-VERIFY1",
        "encounter_id": "ENC-VERIFY1",
        "note_id": "NOTE-VERIFY1",
        "source_system": "EPIC_EMR",
        "note_text": "Patient admitted to ICU with severe sepsis secondary to community-acquired pneumonia. Patient also has pre-existing essential hypertension and type 2 diabetes mellitus."
    }
    ingest_res = handle_ingestion(note_payload)
    print(f"  Ingestion Status: {ingest_res['status']}")
    print(f"  Facts Extracted Count: {ingest_res['extracted_facts_count']}")
    print(f"  Content SHA-256 Hash: {ingest_res['content_hash']}")
    assert ingest_res['status'] in ['ingested', 'duplicate'], "Expected status 'ingested' or 'duplicate'"
    print("  ✅ Note Ingestion & FHIR Bundle generation passed.")

    # Step 3: Test Idempotency (Re-ingesting exact same note)
    print("\n[Step 3] Testing Idempotency (Duplicate Re-ingestion)...")
    duplicate_res = handle_ingestion(note_payload)
    print(f"  Re-ingestion Status: {duplicate_res['status']}")
    print(f"  Message: {duplicate_res['message']}")
    assert duplicate_res['status'] == 'duplicate', "Expected status 'duplicate'"
    print("  ✅ Idempotency check passed (zero duplicate DB entries).")

    # Step 4: Test FHIR REST APIs with Plain ID and FHIR References
    print("\n[Step 4] Testing FHIR Resource Retrieval & Reference Normalization...")
    cond_search_plain = search_fhir_resources("Condition", encounter_id="ENC-VERIFY1")
    cond_search_ref = search_fhir_resources("Condition", encounter_id="Encounter/ENC-VERIFY1")

    print(f"  Conditions found (plain 'ENC-VERIFY1'): {cond_search_plain['total']}")
    print(f"  Conditions found (reference 'Encounter/ENC-VERIFY1'): {cond_search_ref['total']}")
    assert cond_search_plain['total'] > 0, "Expected Condition resources for plain ID"
    assert cond_search_plain['total'] == cond_search_ref['total'], "Plain ID and FHIR reference results must match!"

    patient_res = get_fhir_resource("Patient", "PAT-VERIFY1")
    assert patient_res is not None and patient_res['id'] == "PAT-VERIFY1", "Patient resource lookup failed"

    encounter_res = get_fhir_resource("Encounter", "Encounter/ENC-VERIFY1")
    assert encounter_res is not None and encounter_res['id'] == "ENC-VERIFY1", "Encounter resource reference lookup failed"
    print("  ✅ FHIR REST APIs & Reference Normalization verified successfully.")

    # Step 5: Test Principal Diagnosis Review Engine over HTTP
    print("\n[Step 5] Testing Decoupled Principal Diagnosis Review Engine over HTTP...")
    test_port = 8998
    server = ReusableHTTPServer(("127.0.0.1", test_port), APIRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    try:
        review_req = ReviewRequest(encounter_id="ENC-VERIFY1", fhir_api_base_url=f"http://127.0.0.1:{test_port}")
        review_res = PrincipalDiagnosisReviewEngine.evaluate_encounter(review_req)

        print(f"  Recommendation Status: {review_res.recommendation_status}")
        print(f"  Recommended Principal Diagnosis: {review_res.recommended_condition['icd10_code']} ({review_res.recommended_condition['display_name']})")
        print(f"  Guideline Reference: {review_res.guideline_references[0]}")
        print(f"  Next Action: {review_res.next_action}")

        assert review_res.recommendation_status == "SUPPORTED", "Expected SUPPORTED recommendation"
        assert review_res.recommended_condition['icd10_code'] == "A41.9", "Expected Sepsis (A41.9) as principal diagnosis per Section II.B guidelines"
        print("  ✅ Principal Diagnosis Review Engine verified over HTTP.")
    finally:
        server.shutdown()
        server.server_close()

    # Step 6: Test System Health & Metrics
    print("\n[Step 6] Testing Health & Metrics Endpoint...")
    metrics = get_metrics()
    print(f"  Database Engine: {metrics['database']}")
    print(f"  Total Notes Ingested: {metrics['total_notes_ingested']}")
    print(f"  Total FHIR Resources: {metrics['total_fhir_resources']}")
    assert metrics['total_notes_ingested'] >= 1, "Expected at least 1 note ingested"
    print("  ✅ Health & Metrics endpoint verified.")

    # Step 7: Run All Pytest/Unittest Suites
    print("\n[Step 7] Executing Unit & Integration Test Suites...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestClinicalFactExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestFHIRMapper))
    suite.addTests(loader.loadTestsFromTestCase(TestIdempotency))
    suite.addTests(loader.loadTestsFromTestCase(TestPrincipalDiagnosisReview))
    suite.addTests(loader.loadTestsFromTestCase(TestFHIRSearchNormalization))

    runner = unittest.TextTestRunner(verbosity=1)
    test_result = runner.run(suite)
    assert test_result.wasSuccessful(), "Unit tests failed!"
    print("  ✅ All Unit & Integration Test Suites passed.")

    print("\n" + "=" * 60)
    print("🎉 ALL SYSTEM VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    verify_system()
