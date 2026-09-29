"""
Unit & Persistence Tests for Ingestion Idempotency.
"""

import unittest
from app.database import db
from app.api.ingestion import handle_ingestion


class TestIdempotency(unittest.TestCase):

    def setUp(self):
        db.init_db()
        # Clean up previous test entries to ensure clean baseline for res1
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            if db.is_postgres:
                cursor.execute("DELETE FROM notes WHERE note_id LIKE 'NOTE-IDEM%';")
                cursor.execute("DELETE FROM fhir_resources WHERE encounter_id LIKE 'ENC-IDEM%';")
                cursor.execute("DELETE FROM ingestion_logs WHERE note_id LIKE 'NOTE-IDEM%';")
            else:
                cursor.execute("DELETE FROM notes WHERE note_id LIKE 'NOTE-IDEM%';")
                cursor.execute("DELETE FROM fhir_resources WHERE encounter_id LIKE 'ENC-IDEM%';")
                cursor.execute("DELETE FROM ingestion_logs WHERE note_id LIKE 'NOTE-IDEM%';")
            conn.commit()
        finally:
            conn.close()

    def test_idempotent_reingestion(self):
        payload = {
            "patient_id": "PAT-IDEM1",
            "encounter_id": "ENC-IDEM1",
            "note_id": "NOTE-IDEM1",
            "source_system": "EPIC_EMR",
            "note_text": "Patient presented with acute lower gastrointestinal bleeding due to diverticulosis."
        }

        # First Ingestion
        res1 = handle_ingestion(payload)
        self.assertEqual(res1["status"], "ingested")

        # Second Ingestion (Exact Same Note)
        res2 = handle_ingestion(payload)
        self.assertEqual(res2["status"], "duplicate")
        self.assertEqual(res1["content_hash"], res2["content_hash"])

        # Check DB notes count is 1
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            if db.is_postgres:
                cursor.execute("SELECT COUNT(*) FROM notes WHERE note_id = 'NOTE-IDEM1';")
            else:
                cursor.execute("SELECT COUNT(*) FROM notes WHERE note_id = 'NOTE-IDEM1';")
            count = cursor.fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(count, 1, "Duplicate row was inserted into database!")


if __name__ == "__main__":
    unittest.main()
