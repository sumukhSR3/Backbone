"""
Unit Tests for Deterministic Clinical Fact Extractor.
"""

import unittest
from app.services.extractor import ClinicalFactExtractor


class TestClinicalFactExtractor(unittest.TestCase):

    def test_sepsis_and_pneumonia_extraction(self):
        note = "Patient presented to ED with severe sepsis secondary to community-acquired pneumonia. History of hypertension."
        facts = ClinicalFactExtractor.extract_facts(note, "NOTE-TEST1")

        codes = [f.icd10_code for f in facts]
        self.assertIn("A41.9", codes)  # Sepsis
        self.assertIn("J18.9", codes)  # Pneumonia
        self.assertIn("I10", codes)    # HTN

        sepsis_fact = next(f for f in facts if f.icd10_code == "A41.9")
        self.assertEqual(sepsis_fact.verification_status, "confirmed")
        self.assertEqual(sepsis_fact.present_on_admission, "Y")

    def test_uncertainty_extraction(self):
        note = "Patient discharged with probable acute appendicitis vs suspected diverticulitis."
        facts = ClinicalFactExtractor.extract_facts(note, "NOTE-TEST2")

        codes = [f.icd10_code for f in facts]
        self.assertIn("K35.80", codes)  # Appendicitis
        self.assertIn("K57.32", codes)  # Diverticulitis

        app_fact = next(f for f in facts if f.icd10_code == "K35.80")
        self.assertTrue(app_fact.is_uncertain)
        self.assertEqual(app_fact.verification_status, "provisional")
        self.assertEqual(app_fact.uncertainty_qualifier, "probable")

    def test_negation_extraction(self):
        note = "Patient complains of chest pain. Head CT negative for stroke. No signs of heart attack."
        facts = ClinicalFactExtractor.extract_facts(note, "NOTE-TEST3")

        stroke_fact = next((f for f in facts if f.icd10_code == "I63.9"), None)
        if stroke_fact:
            self.assertTrue(stroke_fact.is_negated)
            self.assertEqual(stroke_fact.verification_status, "refuted")


if __name__ == "__main__":
    unittest.main()
