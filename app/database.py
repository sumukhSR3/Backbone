"""
Database Access Layer - Supports PostgreSQL and SQLite with indexing and transactions.
"""

import os
import json
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config import DATABASE_URL, DEFAULT_SQLITE_PATH


class Database:
    """
    Robust database adapter supporting both PostgreSQL and SQLite.
    Implements clean schema management, unique indexes, and JSON querying.
    """

    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self.is_postgres = db_url.startswith("postgres")

    def get_connection(self):
        if self.is_postgres:
            import psycopg2
            return psycopg2.connect(self.db_url)
        else:
            db_path = self.db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def init_db(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.is_postgres:
                # PostgreSQL schema
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    note_id VARCHAR(128) PRIMARY KEY,
                    encounter_id VARCHAR(128) NOT NULL,
                    patient_id VARCHAR(128) NOT NULL,
                    source_system VARCHAR(128) NOT NULL,
                    content_hash VARCHAR(64) UNIQUE NOT NULL,
                    note_text TEXT NOT NULL,
                    author VARCHAR(256),
                    service VARCHAR(128),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS fhir_resources (
                    id SERIAL PRIMARY KEY,
                    resource_type VARCHAR(64) NOT NULL,
                    resource_id VARCHAR(128) NOT NULL,
                    patient_id VARCHAR(128),
                    encounter_id VARCHAR(128),
                    resource_json JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unq_fhir_resource UNIQUE (resource_type, resource_id)
                );

                CREATE TABLE IF NOT EXISTS ingestion_logs (
                    id SERIAL PRIMARY KEY,
                    note_id VARCHAR(128) NOT NULL,
                    encounter_id VARCHAR(128) NOT NULL,
                    patient_id VARCHAR(128) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    extracted_count INT NOT NULL,
                    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_notes_encounter ON notes(encounter_id);
                CREATE INDEX IF NOT EXISTS idx_notes_patient ON notes(patient_id);
                CREATE INDEX IF NOT EXISTS idx_notes_hash ON notes(content_hash);

                CREATE INDEX IF NOT EXISTS idx_fhir_encounter ON fhir_resources(encounter_id, resource_type);
                CREATE INDEX IF NOT EXISTS idx_fhir_patient ON fhir_resources(patient_id, resource_type);
                CREATE INDEX IF NOT EXISTS idx_fhir_lookup ON fhir_resources(resource_type, resource_id);
                """)
            else:
                # SQLite schema
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    note_id TEXT PRIMARY KEY,
                    encounter_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    note_text TEXT NOT NULL,
                    author TEXT,
                    service TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS fhir_resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    patient_id TEXT,
                    encounter_id TEXT,
                    resource_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(resource_type, resource_id)
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT NOT NULL,
                    encounter_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    extracted_count INTEGER NOT NULL,
                    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_encounter ON notes(encounter_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_patient ON notes(patient_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_hash ON notes(content_hash);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fhir_encounter ON fhir_resources(encounter_id, resource_type);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fhir_patient ON fhir_resources(patient_id, resource_type);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fhir_lookup ON fhir_resources(resource_type, resource_id);")

            conn.commit()
        finally:
            conn.close()


# Global DB instance
db = Database()
