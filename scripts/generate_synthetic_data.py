"""
Synthetic Inpatient Discharge Note Generator.
Generates 1,000+ realistic synthetic clinical encounters and populates the FHIR database.
"""

import sys
import os
import time
import random

sys.path.insert(0, ".")

from app.database import db
from app.schemas import IngestionRequest
from app.api.ingestion import handle_ingestion
from typing import Dict, Any


FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

SCENARIO_TEMPLATES = [
    # Scenario A: Severe Sepsis due to CAP
    {
        "dx": "Sepsis secondary to Community-Acquired Pneumonia",
        "template": """DISCHARGE SUMMARY
Patient: {patient_id} ({name}) | Encounter: {encounter_id}
SERVICE: Internal Medicine / ICU
CHIEF COMPLAINT: Fever, chills, confusion, and acute shortness of breath.

HISTORY OF PRESENT ILLNESS:
The patient is a {age}-year-old {gender} with a history of essential hypertension and type 2 diabetes mellitus who presented to the Emergency Department with severe sepsis secondary to community-acquired pneumonia. At admission, the patient was febrile to 39.1°C, hypotensive (86/52 mmHg), and tachycardic (120 bpm). Laboratory studies demonstrated a leukocytosis of 19.2 k/uL and lactic acidosis of 3.4 mmol/L. Chest radiography confirmed right lower lobe consolidation consistent with acute pneumonia.

HOSPITAL COURSE:
Admitted to ICU for severe sepsis bundle management including broad-spectrum intravenous antibiotics (Vancomycin and Cefepime) and aggressive IV fluid resuscitation. Hemodynamics improved after 48 hours. On hospital day 2, serum creatinine spiked from baseline 0.9 mg/dL to 2.1 mg/dL, consistent with acute kidney injury present on admission due to hypoperfusion. Creatinine normalized prior to discharge.

DISCHARGE DIAGNOSES:
1. Sepsis due to Community-Acquired Pneumonia (Present on Admission)
2. Community-Acquired Pneumonia
3. Acute Kidney Injury (Resolved)
4. Essential Hypertension
5. Type 2 Diabetes Mellitus

DISCHARGE CONDITION: Stable on room air."""
    },

    # Scenario B: Acute Systolic Heart Failure vs COPD
    {
        "dx": "Acute Systolic Heart Failure",
        "template": """DISCHARGE SUMMARY
Patient: {patient_id} ({name}) | Encounter: {encounter_id}
SERVICE: Cardiology / Hospital Medicine
CHIEF COMPLAINT: Severe shortness of breath, orthopnea, and lower extremity edema.

HISTORY OF PRESENT ILLNESS:
A {age}-year-old {gender} with chronic systolic heart failure and chronic obstructive pulmonary disease (COPD) presented with acute shortness of breath and bilateral pitting edema. On admission, oxygen saturation was 86% on room air. Chest X-ray showed acute pulmonary edema and cardiomegaly. Echocardiogram demonstrated an ejection fraction of 25%, confirming acute systolic heart failure exacerbation present on admission.

HOSPITAL COURSE:
Treated with aggressive IV furosemide diuresis with a net negative fluid balance of 4.8 liters over 4 days. Dyspnea dramatically improved. Chronic COPD maintained on inhalers without acute wheezing or exacerbation.

DISCHARGE DIAGNOSES:
1. Acute Systolic Congestive Heart Failure (Present on Admission)
2. Chronic Obstructive Pulmonary Disease (COPD)
3. Essential Hypertension"""
    },

    # Scenario C: GI Bleed & Diverticulosis
    {
        "dx": "Acute Lower Gastrointestinal Bleed",
        "template": """DISCHARGE SUMMARY
Patient: {patient_id} ({name}) | Encounter: {encounter_id}
SERVICE: Gastroenterology / General Surgery
CHIEF COMPLAINT: Hematochezia and acute rectal bleeding with dizziness.

HISTORY OF PRESENT ILLNESS:
A {age}-year-old {gender} presented with acute lower gastrointestinal bleeding. Hemoglobin on admission dropped to 7.6 g/dL baseline requiring 2 units PRBC transfusion. Urgent colonoscopy identified active diverticular bleeding in the sigmoid colon. Hemostasis achieved with endoscopic clip placement.

HOSPITAL COURSE:
Observed for 48 hours post-procedure with stable hemoglobin. No re-bleeding noted.

DISCHARGE DIAGNOSES:
1. Acute Lower Gastrointestinal Bleeding secondary to Sigmoid Diverticulitis with Hemorrhage (Present on Admission)
2. Diverticulosis of large intestine
3. Essential Hypertension"""
    },

    # Scenario D: Unconfirmed Appendicitis vs Diverticulitis (Clarification Needed)
    {
        "dx": "Probable Acute Appendicitis vs Diverticulitis",
        "template": """DISCHARGE SUMMARY
Patient: {patient_id} ({name}) | Encounter: {encounter_id}
SERVICE: General Surgery
CHIEF COMPLAINT: Right lower quadrant abdominal pain and low-grade fever.

HISTORY OF PRESENT ILLNESS:
A {age}-year-old {gender} presented with severe right lower quadrant abdominal pain. Ultrasound showed a thickened non-compressible bowel loop. Discharged with diagnosis of probable acute appendicitis vs diverticulitis requiring outpatient follow-up and surgical consultation.

DISCHARGE DIAGNOSES:
1. Probable Acute Appendicitis
2. Suspected Sigmoid Diverticulitis (Unconfirmed)"""
    },

    # Scenario E: Acute Ischemic Stroke
    {
        "dx": "Acute Ischemic Stroke",
        "template": """DISCHARGE SUMMARY
Patient: {patient_id} ({name}) | Encounter: {encounter_id}
SERVICE: Neurology
CHIEF COMPLAINT: Acute left facial droop and arm weakness.

HISTORY OF PRESENT ILLNESS:
A {age}-year-old {gender} with atrial fibrillation presented within 2 hours of symptom onset. Brain MRI confirmed an acute right middle cerebral artery ischemic stroke. IV tPA administered with significant recovery.

DISCHARGE DIAGNOSES:
1. Acute Ischemic Stroke / Cerebral Infarction (Present on Admission)
2. Atrial Fibrillation
3. Essential Hypertension"""
    }
]


def generate_synthetic_data(count: int = 1000) -> Dict[str, Any]:
    print(f"⚡ Starting synthetic generation for {count} inpatient encounters...")
    db.init_db()

    start_time = time.time()
    success_count = 0
    duplicate_count = 0
    total_facts = 0

    for i in range(1, count + 1):
        patient_num = 1000 + (i % 250)
        patient_id = f"PAT-{patient_num}"
        encounter_id = f"ENC-{20000 + i}"
        note_id = f"NOTE-{30000 + i}"

        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age = random.randint(35, 88)
        gender = random.choice(["male", "female"])

        template_obj = SCENARIO_TEMPLATES[(i - 1) % len(SCENARIO_TEMPLATES)]
        note_text = template_obj["template"].format(
            patient_id=patient_id,
            encounter_id=encounter_id,
            name=name,
            age=age,
            gender=gender
        )

        req_dict = {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "note_id": note_id,
            "source_system": "EPIC_EMR",
            "note_text": note_text,
            "author": f"Dr. {random.choice(LAST_NAMES)}",
            "service": "Internal Medicine"
        }

        res = handle_ingestion(req_dict)
        if res.get("status") == "ingested":
            success_count += 1
            total_facts += res.get("extracted_facts_count", 0)
        else:
            duplicate_count += 1

        if i % 200 == 0 or i == count:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  Processed {i}/{count} notes... ({rate:.1f} notes/sec)")

    elapsed = time.time() - start_time
    rate = count / elapsed if elapsed > 0 else 0

    summary = {
        "requested_count": count,
        "successfully_ingested": success_count,
        "duplicates_skipped": duplicate_count,
        "total_extracted_facts": total_facts,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_notes_per_sec": round(rate, 2),
    }

    print("\n✅ Synthetic Generation Complete!")
    print(f"   • Total Notes Ingested: {success_count}")
    print(f"   • Total Clinical Facts Extracted: {total_facts}")
    print(f"   • Time Taken: {elapsed:.2f}s ({rate:.1f} notes/sec)")

    return summary


if __name__ == "__main__":
    count_arg = 1000
    if len(sys.argv) > 1:
        try:
            count_arg = int(sys.argv[1])
        except ValueError:
            pass
    generate_synthetic_data(count_arg)
