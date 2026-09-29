# End-to-End Clinical Data Ingestion & FY 2026 ICD-10-CM Principal Diagnosis Review System

> A production-minded, decoupled system for ingesting discharge notes, extracting clinical facts deterministically, mapping to inspectable FHIR R4 Bundles, persisting idempotently in PostgreSQL, exposing FHIR REST APIs, and evaluating ICD-10-CM Principal Diagnosis guidelines over HTTP.

---

## 🌟 Key Features

- **Clinical Note Ingestion**: Ingests 200–400 word inpatient discharge notes with metadata (`patient_id`, `encounter_id`, `note_id`, `source_system`).
- **Deterministic NLP Fact Extraction**: Extracts diagnoses, ICD-10-CM codes, Present on Admission (POA) flags, acuity, negation, and uncertainty qualifiers (`probable`, `suspected`, `rule out`, `likely`).
- **Inspectable FHIR R4 Bundle Mapping**: Maps extracted facts and original note text into compliant FHIR R4 resources: `Patient`, `Encounter`, `Condition`, `DocumentReference`, `Binary`, and `Bundle`. Validates all resource schema references.
- **Idempotent PostgreSQL Storage**: Computes SHA-256 fingerprints of note content to guarantee 100% idempotent re-ingestion with zero data bloat or duplicate FHIR entries.
- **FHIR REST APIs**: Standard HTTP endpoints to retrieve individual resources (`/fhir/Patient/{id}`, `/fhir/Condition/{id}`, etc.) and search by encounter/patient (`/fhir/Condition?encounter={id}`).
- **Decoupled Principal Diagnosis Review Component**: Takes **only** an `encounter_id` and `fhir_api_base_url`. Retrieves Encounter, Conditions, and Note strictly over HTTP—without reading PostgreSQL or ingestion inputs directly—and applies FY 2026 ICD-10-CM Section II guidelines.
- **Interactive Web Dashboard**: Live web UI for ingesting notes, inspecting FHIR JSON, running principal diagnosis reviews, and monitoring system metrics.
- **Synthetic Data & Load Testing**: Generates 1,000+ realistic synthetic encounters and benchmarks system throughput, latency, and query index performance.

---

## 🏗️ Architecture & Component Flow

```
[Clinical Note / EHR]
        │
        ▼
[1. Ingestion API: POST /api/v1/ingest]
        │
        ▼
[2. Deterministic Extraction Engine] ---> (Negation, Uncertainty, POA, ICD-10)
        │
        ▼
[3. FHIR R4 Builder & Schema Validator] ---> (Patient, Encounter, Condition, DocRef, Binary)
        │
        ▼
[4. Idempotent PostgreSQL Persistence] ---> (SHA-256 Fingerprint & Unique Indexes)
        │
        ▼
[5. FHIR REST APIs: GET /fhir/...]
        ▲
        │  (Strict HTTP REST Calls Only)
        │
[6. Decoupled Principal Diagnosis Review Engine]
        │
        ▼  (Applies FY 2026 ICD-10-CM Guidelines: Sec II.A, II.B, II.C, II.D, II.G)
[7. Recommendation Output] ---> (SUPPORTED / CLARIFICATION_NEEDED, Guideline Citations, Passages)
```

---

## 🚀 Quick Start & Installation

### Option A: Running with Docker Compose (FastAPI + PostgreSQL)

```bash
# 1. Clone or navigate to project directory
cd Backbone

# 2. Build and start services using Docker Compose
docker compose up --build -d

# 3. Access the Web Dashboard at:
# http://localhost:8000
```

### Option B: Running Locally with Native Python 3 (Zero Dependencies Required)

```bash
# 1. Run the local dev server (uses Python 3 standard library + SQLite DB)
python3 run_dev.py

# 2. Open your browser at:
# http://localhost:8000
```

---

## 🧪 Running Tests & Benchmarks

### 1. Run Master Test Suite
Executes unit tests for extraction, FHIR mapping, idempotency, and review rules:

```bash
python3 tests/test_runner.py
```

### 2. Generate 1,000 Synthetic Clinical Encounters
Populates the database with 1,000 realistic inpatient discharge notes:

```bash
python3 scripts/generate_synthetic_data.py 1000
```

### 3. Run Performance Benchmarks & Index Evidence
Measures ingestion throughput, FHIR search latency, review latency, and verifies database indexes:

```bash
python3 scripts/run_benchmarks.py
```

---

## 📡 API Reference

### 1. Ingest Clinical Note
**`POST /api/v1/ingest`**
```json
{
  "patient_id": "PAT-8801",
  "encounter_id": "ENC-9901",
  "note_id": "NOTE-7701",
  "source_system": "EPIC_EMR",
  "note_text": "Patient presented with severe sepsis secondary to community-acquired pneumonia..."
}
```

### 2. Retrieve FHIR Resource
**`GET /fhir/Condition/COND-7701-A419`**
**`GET /fhir/Patient/PAT-8801`**
**`GET /fhir/DocumentReference/DOCREF-7701`**

### 3. Search FHIR Conditions by Encounter
**`GET /fhir/Condition?encounter=ENC-9901`**

### 4. Run Principal Diagnosis Review
**`POST /api/v1/review/principal-diagnosis`**
```json
{
  "encounter_id": "ENC-9901",
  "fhir_api_base_url": "http://localhost:8000"
}
```

#### Sample Review Output:
```json
{
  "encounter_id": "ENC-9901",
  "recommendation_status": "SUPPORTED",
  "recommended_condition": {
    "condition_id": "COND-7701-A419",
    "icd10_code": "A41.9",
    "display_name": "Sepsis, unspecified organism",
    "verification_status": "confirmed",
    "acuity": "acute",
    "present_on_admission": "Y"
  },
  "supporting_passages": [
    "The patient presented with severe sepsis secondary to community-acquired pneumonia."
  ],
  "guideline_references": [
    "FY 2026 ICD-10-CM Guidelines Section II.B: Sepsis is sequenced as principal diagnosis when secondary to a localized infection present on admission."
  ],
  "competing_possibilities": [
    {
      "icd10_code": "J18.9",
      "display_name": "Pneumonia, unspecified organism",
      "verification_status": "confirmed",
      "exclusion_reason": "Sequenced after Sepsis based on acuity, POA status, and ICD-10-CM Section II guidelines."
    }
  ],
  "next_action": "Approve draft recommendation: assign A41.9 (Sepsis, unspecified organism) as principal diagnosis."
}
```

---

## 📖 System Design & Production Sizing

For details on scaling to **100,000 notes/day** and **10,000,000 FHIR resources**, Kafka ingestion queues, Redis distributed locking, database partitioning, and stale review invalidation, refer to [`DESIGN_DOC.md`](file:///Users/sumukhramagiri/Desktop/Backbone/DESIGN_DOC.md).
