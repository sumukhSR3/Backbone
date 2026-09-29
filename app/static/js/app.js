const PRESETS = {
  sepsis: `DISCHARGE SUMMARY
Patient: PAT-8801 | Encounter: ENC-9901
SERVICE: Internal Medicine / ICU
CHIEF COMPLAINT: High fever, chills, confusion, and acute shortness of breath.

HISTORY OF PRESENT ILLNESS:
The patient is a 68-year-old male with a history of essential hypertension and type 2 diabetes mellitus who presented to the Emergency Department with severe sepsis secondary to community-acquired pneumonia. At admission, the patient was febrile to 38.9°C, hypotensive (88/54 mmHg), and tachycardic (118 bpm). Laboratory studies demonstrated a leukocytosis of 18.4 k/uL and lactic acidosis of 3.2 mmol/L. Chest radiography confirmed a right lower lobe consolidation consistent with acute pneumonia.

HOSPITAL COURSE:
The patient was admitted to the Intensive Care Unit and initiated on intravenous broad-spectrum antibiotics (Vancomycin and Cefepime) and aggressive fluid resuscitation. Sepsis bundle protocol was completed within 3 hours. Hemodynamics stabilized over 48 hours and blood cultures remained negative. On hospital day 3, serum creatinine transiently spiked consistent with mild acute kidney injury (resolved prior to discharge).

DISCHARGE DIAGNOSES:
1. Sepsis due to Community-Acquired Pneumonia (Present on Admission)
2. Community-Acquired Pneumonia
3. Resolved Acute Kidney Injury
4. Essential Hypertension (Pre-existing)
5. Type 2 Diabetes Mellitus (Pre-existing)

DISCHARGE CONDITION: Stable. Oxygen saturation 97% on room air.`,

  heart_failure: `DISCHARGE SUMMARY
Patient: PAT-8802 | Encounter: ENC-9902
SERVICE: Cardiology / Hospital Medicine
CHIEF COMPLAINT: Severe shortness of breath, orthopnea, and bilateral lower extremity edema.

HISTORY OF PRESENT ILLNESS:
A 72-year-old female with chronic systolic heart failure and chronic obstructive pulmonary disease (COPD) admitted with acute shortness of breath. On admission, oxygen saturation was 85% on room air. Physical exam revealed diffuse crackles and bilateral 3+ pitting edema. Chest X-ray showed acute pulmonary edema and cardiomegaly. Echocardiogram demonstrated an ejection fraction of 25%, confirming acute systolic heart failure exacerbation.

HOSPITAL COURSE:
The patient received aggressive IV furosemide diuresis with total fluid balance of -4.5 liters over 4 days. Dyspnea dramatically improved. Chronic COPD was maintained on daily tiotropium without acute wheezing or exacerbation.

DISCHARGE DIAGNOSES:
1. Acute Systolic Congestive Heart Failure (Present on Admission)
2. Chronic Obstructive Pulmonary Disease (COPD)
3. Essential Hypertension`,

  gi_bleed: `DISCHARGE SUMMARY
Patient: PAT-8803 | Encounter: ENC-9903
SERVICE: Gastroenterology / General Surgery
CHIEF COMPLAINT: Hematochezia and acute rectal bleeding with dizziness.

HISTORY OF PRESENT ILLNESS:
A 65-year-old male presented to the ED with large-volume bright red blood per rectum. Hemoglobin on admission dropped to 7.8 g/dL (baseline 13.5 g/dL) requiring 2 units of PRBC transfusion. Urgent colonoscopy identified active diverticular bleeding in the sigmoid colon. Hemostasis achieved with endoscopic clip placement.

DISCHARGE DIAGNOSES:
1. Acute Lower Gastrointestinal Bleeding secondary to Sigmoid Diverticulosis with Hemorrhage (Present on Admission)
2. Diverticulosis of large intestine
3. Acute Post-hemorrhagic Anemia`,

  appendicitis: `DISCHARGE SUMMARY
Patient: PAT-8804 | Encounter: ENC-9904
SERVICE: General Surgery
CHIEF COMPLAINT: Right lower quadrant abdominal pain and low-grade fever.

HISTORY OF PRESENT ILLNESS:
A 41-year-old female admitted for severe right lower quadrant abdominal pain. Abdominal ultrasound demonstrated a non-compressible fluid-filled blind-ended tubular structure measuring 8 mm in diameter. Discharged with diagnosis of probable acute appendicitis vs diverticulitis, requiring outpatient follow-up.

DISCHARGE DIAGNOSES:
1. Probable Acute Appendicitis
2. Suspected Sigmoid Diverticulitis (Unconfirmed)`,

  stroke: `DISCHARGE SUMMARY
Patient: PAT-8805 | Encounter: ENC-9905
SERVICE: Neurology
CHIEF COMPLAINT: Acute onset left-sided facial droop and arm weakness.

HISTORY OF PRESENT ILLNESS:
A 75-year-old male with atrial fibrillation presented within 2 hours of symptom onset. Brain MRI confirmed an acute right middle cerebral artery ischemic stroke. IV tPA administered with significant neurological recovery.

DISCHARGE DIAGNOSES:
1. Acute Ischemic Stroke / Cerebral Infarction (Present on Admission)
2. Atrial Fibrillation
3. Essential Hypertension`
};

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
  
  event.target.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

function loadPreset() {
  const val = document.getElementById('preset-select').value;
  if (PRESETS[val]) {
    document.getElementById('note-text').value = PRESETS[val];
    if (val === 'sepsis') {
      document.getElementById('patient-id').value = 'PAT-8801';
      document.getElementById('encounter-id').value = 'ENC-9901';
      document.getElementById('note-id').value = 'NOTE-7701';
    } else if (val === 'heart_failure') {
      document.getElementById('patient-id').value = 'PAT-8802';
      document.getElementById('encounter-id').value = 'ENC-9902';
      document.getElementById('note-id').value = 'NOTE-7702';
    } else if (val === 'gi_bleed') {
      document.getElementById('patient-id').value = 'PAT-8803';
      document.getElementById('encounter-id').value = 'ENC-9903';
      document.getElementById('note-id').value = 'NOTE-7703';
    } else if (val === 'appendicitis') {
      document.getElementById('patient-id').value = 'PAT-8804';
      document.getElementById('encounter-id').value = 'ENC-9904';
      document.getElementById('note-id').value = 'NOTE-7704';
    } else if (val === 'stroke') {
      document.getElementById('patient-id').value = 'PAT-8805';
      document.getElementById('encounter-id').value = 'ENC-9905';
      document.getElementById('note-id').value = 'NOTE-7705';
    }
  }
}

async function ingestNote(isIdempotentTest = false) {
  const payload = {
    patient_id: document.getElementById('patient-id').value,
    encounter_id: document.getElementById('encounter-id').value,
    note_id: document.getElementById('note-id').value,
    source_system: document.getElementById('source-system').value,
    note_text: document.getElementById('note-text').value,
  };

  const statusEl = document.getElementById('ingest-status');
  const jsonEl = document.getElementById('ingest-json');
  statusEl.innerHTML = '<span class="badge badge-info">Processing Ingestion & Fact Extraction...</span>';

  try {
    const resp = await fetch('/api/v1/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    jsonEl.textContent = JSON.stringify(data, null, 2);

    if (data.status === 'duplicate') {
      statusEl.innerHTML = `<span class="badge badge-warning">IDEMPOTENT RE-INGESTION DETECTED: Hash ${data.content_hash.substring(0, 12)}... already stored!</span>`;
    } else {
      statusEl.innerHTML = `<span class="badge badge-success">INGESTION SUCCESSFUL: ${data.extracted_facts_count} Clinical Facts Extracted & FHIR R4 Bundle Created</span>`;
    }

    // Update search/review inputs automatically
    document.getElementById('search-enc-id').value = payload.encounter_id;
    document.getElementById('review-enc-id').value = payload.encounter_id;
    fetchMetrics();
  } catch (err) {
    statusEl.innerHTML = `<span class="badge badge-danger">Ingestion Error: ${err.message}</span>`;
  }
}

async function searchFhir() {
  const encId = document.getElementById('search-enc-id').value;
  try {
    const condResp = await fetch(`/fhir/Condition?encounter=${encId}`);
    const condData = await condResp.json();
    document.getElementById('fhir-conditions-json').textContent = JSON.stringify(condData, null, 2);

    const docResp = await fetch(`/fhir/DocumentReference?encounter=${encId}`);
    const docData = await docResp.json();
    document.getElementById('fhir-docref-json').textContent = JSON.stringify(docData, null, 2);
  } catch (err) {
    alert("FHIR Search error: " + err.message);
  }
}

async function runReview() {
  const encId = document.getElementById('review-enc-id').value;
  const baseUrl = document.getElementById('review-base-url').value;

  const statusHeader = document.getElementById('review-status-header');
  const jsonEl = document.getElementById('review-json');
  statusHeader.innerHTML = '<span class="badge badge-info">Fetching FHIR Resources over HTTP & Evaluating FY 2026 ICD-10 Rules...</span>';

  try {
    const resp = await fetch('/api/v1/review/principal-diagnosis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ encounter_id: encId, fhir_api_base_url: baseUrl })
    });
    const data = await resp.json();
    jsonEl.textContent = JSON.stringify(data, null, 2);

    if (data.recommendation_status === 'SUPPORTED') {
      statusHeader.innerHTML = `<span class="badge badge-success">RECOMMENDATION: SUPPORTED - ${data.recommended_condition?.icd10_code} (${data.recommended_condition?.display_name})</span>`;
    } else if (data.recommendation_status === 'CLARIFICATION_NEEDED') {
      statusHeader.innerHTML = `<span class="badge badge-warning">RECOMMENDATION: CLARIFICATION NEEDED - Physician Query Required</span>`;
    } else {
      statusHeader.innerHTML = `<span class="badge badge-danger">RECOMMENDATION: UNSUPPORTED</span>`;
    }
  } catch (err) {
    statusHeader.innerHTML = `<span class="badge badge-danger">Review Error: ${err.message}</span>`;
  }
}

async function fetchMetrics() {
  try {
    const resp = await fetch('/api/v1/metrics');
    const data = await resp.json();
    document.getElementById('metrics-json').textContent = JSON.stringify(data, null, 2);
    document.getElementById('db-badge').textContent = `DB: ${data.database}`;
    document.getElementById('stats-badge').textContent = `${data.total_notes_ingested} Notes | ${data.total_fhir_resources} FHIR Resources`;
  } catch (err) {
    console.error("Failed to fetch metrics", err);
  }
}

// Initial setup on load
document.addEventListener('DOMContentLoaded', () => {
  loadPreset();
  fetchMetrics();
});
