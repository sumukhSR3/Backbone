"""
Master Pytest / Unittest Runner script.
Executes all test suites: extraction, fhir_mapping, idempotency, review engine, reference normalization.
"""

import sys
import os
import unittest

sys.path.insert(0, ".")

from tests.test_extraction import TestClinicalFactExtractor
from tests.test_fhir_mapping import TestFHIRMapper
from tests.test_idempotency import TestIdempotency
from tests.test_principal_diagnosis_review import TestPrincipalDiagnosisReview
from tests.test_fhir_search_normalization import TestFHIRSearchNormalization


def run_all_tests():
    print("🧪 Running Master Clinical Data & Review Test Suite...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestClinicalFactExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestFHIRMapper))
    suite.addTests(loader.loadTestsFromTestCase(TestIdempotency))
    suite.addTests(loader.loadTestsFromTestCase(TestPrincipalDiagnosisReview))
    suite.addTests(loader.loadTestsFromTestCase(TestFHIRSearchNormalization))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
