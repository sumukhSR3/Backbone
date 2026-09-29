"""
System Metrics and Query Performance Evidence Handler.
"""

from typing import Dict, Any
from app.database import db


def get_metrics() -> Dict[str, Any]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()

        if db.is_postgres:
            cursor.execute("SELECT COUNT(*) FROM notes;")
            note_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM fhir_resources;")
            resource_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM fhir_resources WHERE resource_type = 'Condition';")
            condition_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ingestion_logs;")
            log_count = cursor.fetchone()[0]
            db_type = "PostgreSQL"
        else:
            cursor.execute("SELECT COUNT(*) FROM notes;")
            note_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM fhir_resources;")
            resource_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM fhir_resources WHERE resource_type = 'Condition';")
            condition_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ingestion_logs;")
            log_count = cursor.fetchone()[0]
            db_type = "SQLite (Local Dev)"

        return {
            "status": "healthy",
            "database": db_type,
            "total_notes_ingested": note_count,
            "total_fhir_resources": resource_count,
            "total_conditions_stored": condition_count,
            "total_ingestion_logs": log_count,
            "indexes_active": [
                "idx_notes_encounter (encounter_id)",
                "idx_notes_patient (patient_id)",
                "idx_notes_hash (content_hash) [UNIQUE]",
                "idx_fhir_encounter (encounter_id, resource_type)",
                "idx_fhir_patient (patient_id, resource_type)",
                "idx_fhir_lookup (resource_type, resource_id) [UNIQUE]",
            ]
        }
    finally:
        conn.close()
