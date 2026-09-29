"""
Idempotent Persistence Service for Notes and FHIR Resources.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from app.database import db
from app.schemas import IngestionRequest, ExtractedFact, IngestionResult
from datetime import datetime


def normalize_id(val: Optional[str]) -> Optional[str]:
    """
    Normalizes FHIR resource references into plain target identifiers.
    Examples:
      - 'Encounter/ENC-9901' -> 'ENC-9901'
      - 'Patient/PAT-8801' -> 'PAT-8801'
      - 'http://localhost:8000/fhir/Encounter/ENC-9901' -> 'ENC-9901'
      - 'urn:uuid:ENC-9901' -> 'ENC-9901'
      - 'ENC-9901' -> 'ENC-9901'
    """
    if not val:
        return None
    val = str(val).strip()
    if "/" in val:
        val = val.rsplit("/", 1)[-1]
    if ":" in val and val.startswith("urn:"):
        val = val.rsplit(":", 1)[-1]
    return val


class StorageService:
    """
    Handles idempotent ingestion and database persistence for clinical notes and FHIR resources.
    """

    @staticmethod
    def compute_hash(text: str, note_id: str = "", encounter_id: str = "") -> str:
        """
        Computes SHA-256 fingerprint for note content and identity.
        """
        payload = f"{note_id}:{encounter_id}:{text.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def ingest_note(
        request: IngestionRequest,
        facts: List[ExtractedFact],
        bundle: Dict[str, Any]
    ) -> IngestionResult:
        content_hash = StorageService.compute_hash(request.note_text, request.note_id, request.encounter_id)
        conn = db.get_connection()

        try:
            cursor = conn.cursor()

            # 1. Idempotency Check: Check if hash already exists
            if db.is_postgres:
                cursor.execute("SELECT note_id FROM notes WHERE content_hash = %s OR note_id = %s;", (content_hash, request.note_id))
            else:
                cursor.execute("SELECT note_id FROM notes WHERE content_hash = ? OR note_id = ?;", (content_hash, request.note_id))
            
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return IngestionResult(
                    status="duplicate",
                    note_id=request.note_id,
                    encounter_id=request.encounter_id,
                    patient_id=request.patient_id,
                    content_hash=content_hash,
                    extracted_facts_count=len(facts),
                    fhir_bundle=bundle,
                    created_at=datetime.utcnow().isoformat() + "Z",
                    message="Idempotent re-ingestion: note content already stored.",
                )

            # 2. Insert Note
            created_at = datetime.utcnow().isoformat() + "Z"
            if db.is_postgres:
                cursor.execute(
                    """
                    INSERT INTO notes (note_id, encounter_id, patient_id, source_system, content_hash, note_text, author, service, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                    """,
                    (request.note_id, request.encounter_id, request.patient_id, request.source_system, content_hash, request.note_text, request.author, request.service)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO notes (note_id, encounter_id, patient_id, source_system, content_hash, note_text, author, service, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
                    """,
                    (request.note_id, request.encounter_id, request.patient_id, request.source_system, content_hash, request.note_text, request.author, request.service)
                )

            # 3. Store FHIR Resources
            entries = bundle.get("entry", [])
            for entry in entries:
                res = entry.get("resource", {})
                rtype = res.get("resourceType")
                rid = res.get("id")
                json_str = json.dumps(res)

                if db.is_postgres:
                    cursor.execute(
                        """
                        INSERT INTO fhir_resources (resource_type, resource_id, patient_id, encounter_id, resource_json)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (resource_type, resource_id) DO UPDATE
                        SET resource_json = EXCLUDED.resource_json;
                        """,
                        (rtype, rid, request.patient_id, request.encounter_id, json_str)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO fhir_resources (resource_type, resource_id, patient_id, encounter_id, resource_json)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (rtype, rid, request.patient_id, request.encounter_id, json_str)
                    )

            # 4. Ingestion Log Entry
            if db.is_postgres:
                cursor.execute(
                    """
                    INSERT INTO ingestion_logs (note_id, encounter_id, patient_id, content_hash, status, extracted_count)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (request.note_id, request.encounter_id, request.patient_id, content_hash, "ingested", len(facts))
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO ingestion_logs (note_id, encounter_id, patient_id, content_hash, status, extracted_count)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (request.note_id, request.encounter_id, request.patient_id, content_hash, "ingested", len(facts))
                )

            conn.commit()

            return IngestionResult(
                status="ingested",
                note_id=request.note_id,
                encounter_id=request.encounter_id,
                patient_id=request.patient_id,
                content_hash=content_hash,
                extracted_facts_count=len(facts),
                fhir_bundle=bundle,
                created_at=created_at,
                message="Note successfully ingested, extracted, and persisted.",
            )

        finally:
            conn.close()

    @staticmethod
    def get_fhir_resource(resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
        norm_rid = normalize_id(resource_id)
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            if db.is_postgres:
                cursor.execute(
                    "SELECT resource_json FROM fhir_resources WHERE resource_type = %s AND resource_id = %s;",
                    (resource_type, norm_rid)
                )
            else:
                cursor.execute(
                    "SELECT resource_json FROM fhir_resources WHERE resource_type = ? AND resource_id = ?;",
                    (resource_type, norm_rid)
                )

            row = cursor.fetchone()
            if not row:
                return None
            val = row[0] if isinstance(row, tuple) else row["resource_json"]
            return json.loads(val) if isinstance(val, str) else val
        finally:
            conn.close()

    @staticmethod
    def search_fhir_resources(
        resource_type: str,
        encounter_id: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        norm_enc = normalize_id(encounter_id)
        norm_pat = normalize_id(patient_id)
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT resource_json FROM fhir_resources WHERE resource_type = "
            params = []

            if db.is_postgres:
                query += "%s"
                params.append(resource_type)
                if norm_enc:
                    query += " AND encounter_id = %s"
                    params.append(norm_enc)
                if norm_pat:
                    query += " AND patient_id = %s"
                    params.append(norm_pat)
            else:
                query += "?"
                params.append(resource_type)
                if norm_enc:
                    query += " AND encounter_id = ?"
                    params.append(norm_enc)
                if norm_pat:
                    query += " AND patient_id = ?"
                    params.append(norm_pat)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                val = row[0] if isinstance(row, tuple) else row["resource_json"]
                results.append(json.loads(val) if isinstance(val, str) else val)
            return results
        finally:
            conn.close()

    @staticmethod
    def get_note_by_encounter(encounter_id: str) -> Optional[Dict[str, Any]]:
        norm_enc = normalize_id(encounter_id)
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            if db.is_postgres:
                cursor.execute("SELECT note_id, encounter_id, patient_id, source_system, note_text, created_at FROM notes WHERE encounter_id = %s ORDER BY created_at DESC LIMIT 1;", (norm_enc,))
            else:
                cursor.execute("SELECT note_id, encounter_id, patient_id, source_system, note_text, created_at FROM notes WHERE encounter_id = ? ORDER BY created_at DESC LIMIT 1;", (norm_enc,))
            row = cursor.fetchone()
            if not row:
                return None
            if isinstance(row, tuple):
                return {
                    "note_id": row[0],
                    "encounter_id": row[1],
                    "patient_id": row[2],
                    "source_system": row[3],
                    "note_text": row[4],
                    "created_at": str(row[5]),
                }
            else:
                return {
                    "note_id": row["note_id"],
                    "encounter_id": row["encounter_id"],
                    "patient_id": row["patient_id"],
                    "source_system": row["source_system"],
                    "note_text": row["note_text"],
                    "created_at": str(row["created_at"]),
                }
        finally:
            conn.close()
