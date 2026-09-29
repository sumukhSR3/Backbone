"""
Deterministic Clinical Fact Extractor.
Extracts diagnoses, ICD-10-CM codes, uncertainty, negation, present on admission (POA),
acuity, and supporting text snippets from discharge notes.
"""

import re
import uuid
from typing import List, Dict, Any, Optional
from app.schemas import ExtractedFact


# Master Dictionary of Clinical Concepts mapped to ICD-10-CM codes and canonical displays
ICD10_DICTIONARY = [
    # Severe systemic / Infectious
    {
        "patterns": [r"\bsepsis\b", r"\bsepticemia\b", r"\bsevere sepsis\b"],
        "code": "A41.9",
        "display": "Sepsis, unspecified organism",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bseptic shock\b"],
        "code": "R65.21",
        "display": "Severe sepsis with septic shock",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bpneumonia\b", r"\bcommunity[\s-]acquired pneumonia\b", r"\bcap\b"],
        "code": "J18.9",
        "display": "Pneumonia, unspecified organism",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\burinary tract infection\b", r"\buti\b", r"\bpyelonephritis\b"],
        "code": "N39.0",
        "display": "Urinary tract infection, site not specified",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    # Respiratory
    {
        "patterns": [r"\bacute respiratory failure\b", r"\brespiratory failure\b"],
        "code": "J96.00",
        "display": "Acute respiratory failure, unspecified whether with hypoxia or hypercapnia",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bcopd exacerbation\b", r"\bacute exacerbation of copd\b", r"\bcopd with acute exacerbation\b"],
        "code": "J44.1",
        "display": "Chronic obstructive pulmonary disease with (acute) exacerbation",
        "category": "encounter-diagnosis",
        "acuity": "acute-on-chronic",
    },
    {
        "patterns": [r"\bchronic obstructive pulmonary disease\b", r"\bcopd\b"],
        "code": "J44.9",
        "display": "Chronic obstructive pulmonary disease, unspecified",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    # Cardiovascular
    {
        "patterns": [r"\bacute systolic heart failure\b", r"\bacute systolic congestive heart failure\b", r"\bacute chf\b"],
        "code": "I50.21",
        "display": "Acute systolic (congestive) heart failure",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bchronic systolic heart failure\b", r"\bchronic chf\b"],
        "code": "I50.22",
        "display": "Chronic systolic (congestive) heart failure",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    {
        "patterns": [r"\bcongestive heart failure\b", r"\bheart failure\b", r"\bchf\b"],
        "code": "I50.9",
        "display": "Heart failure, unspecified",
        "category": "encounter-diagnosis",
        "acuity": "unspecified",
    },
    {
        "patterns": [r"\bacute myocardial infarction\b", r"\bstemi\b", r"\bnstemi\b", r"\bheart attack\b"],
        "code": "I21.9",
        "display": "Acute myocardial infarction, unspecified",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bhypertension\b", r"\bessential hypertension\b", r"\bhtn\b"],
        "code": "I10",
        "display": "Essential (primary) hypertension",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    {
        "patterns": [r"\batrial fibrillation\b", r"\ba-fib\b", r"\bafib\b"],
        "code": "I48.91",
        "display": "Unspecified atrial fibrillation",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    # Renal / GI / Surgical
    {
        "patterns": [r"\bacute kidney injury\b", r"\baki\b", r"\bacute renal failure\b"],
        "code": "N17.9",
        "display": "Acute kidney failure, unspecified",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bchronic kidney disease\b", r"\bckd\b"],
        "code": "N18.9",
        "display": "Chronic kidney disease, unspecified",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    {
        "patterns": [r"\bgastrointestinal bleed\b", r"\bgi bleed\b", r"\blower gi bleed\b", r"\bgastrointestinal hemorrhage\b"],
        "code": "K92.2",
        "display": "Gastrointestinal hemorrhage, unspecified",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bdiverticulitis\b", r"\bdiverticulitis with hemorrhage\b"],
        "code": "K57.32",
        "display": "Diverticulitis of large intestine with hemorrhage",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bdiverticulosis\b"],
        "code": "K57.30",
        "display": "Diverticulosis of large intestine without perforation or abscess",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    {
        "patterns": [r"\bacute appendicitis\b", r"\bappendicitis\b"],
        "code": "K35.80",
        "display": "Unspecified acute appendicitis",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bacute pancreatitis\b", r"\bpancreatitis\b"],
        "code": "K85.90",
        "display": "Acute pancreatitis, unspecified without necrosis or infection",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    # Neurological / Endocrine
    {
        "patterns": [r"\bischemic stroke\b", r"\bcerebral infarction\b", r"\bcva\b", r"\bstroke\b"],
        "code": "I63.9",
        "display": "Cerebral infarction, unspecified",
        "category": "encounter-diagnosis",
        "acuity": "acute",
    },
    {
        "patterns": [r"\btype 2 diabetes\b", r"\btype ii diabetes\b", r"\bdiabetes mellitus\b", r"\bdm2\b", r"\bt2dm\b"],
        "code": "E11.9",
        "display": "Type 2 diabetes mellitus without complications",
        "category": "problem-list-item",
        "acuity": "chronic",
    },
    # Symptoms / Signs (Section II.A candidates)
    {
        "patterns": [r"\bchest pain\b"],
        "code": "R07.9",
        "display": "Chest pain, unspecified",
        "category": "chief-complaint",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bshortness of breath\b", r"\bdyspnea\b", r"\bsob\b"],
        "code": "R06.02",
        "display": "Shortness of breath",
        "category": "chief-complaint",
        "acuity": "acute",
    },
    {
        "patterns": [r"\babdominal pain\b"],
        "code": "R10.9",
        "display": "Unspecified abdominal pain",
        "category": "chief-complaint",
        "acuity": "acute",
    },
    {
        "patterns": [r"\bfever\b", r"\bpyrexia\b"],
        "code": "R50.9",
        "display": "Fever, unspecified",
        "category": "chief-complaint",
        "acuity": "acute",
    },
]

# Modifiers regex definitions
NEGATION_PATTERNS = [
    r"\bno\b", r"\bdenies\b", r"\bdenied\b", r"\bnegative for\b",
    r"\bwithout evidence of\b", r"\bruled out\b", r"\bruling out\b",
    r"\bno signs of\b", r"\bno symptoms of\b", r"\babsent\b", r"\bunlikely\b"
]

UNCERTAINTY_PATTERNS = [
    (r"\bprobable\b", "probable"),
    (r"\bpossible\b", "possible"),
    (r"\bsuspected\b", "suspected"),
    (r"\brule out\b", "rule out"),
    (r"\br/o\b", "rule out"),
    (r"\blikely\b", "likely"),
    (r"\bprovisional\b", "provisional"),
    (r"\bconcern for\b", "suspected"),
    (r"\bpresumed\b", "presumed")
]

POA_YES_PATTERNS = [
    r"\badmitted with\b", r"\bpresent on admission\b", r"\bhistory of\b",
    r"\bh/o\b", r"\bchronic\b", r"\bon presentation\b", r"\bchief complaint of\b",
    r"\bpresented with\b", r"\bpre-existing\b", r"\bat admission\b"
]

POA_NO_PATTERNS = [
    r"\bhospital[\s-]acquired\b", r"\bdeveloped on hospital day\b", r"\bpost-procedure\b",
    r"\bnosocomial\b", r"\bcomplication of\b", r"\bduring hospital stay\b", r"\bon day \d+\b"
]

RESOLVED_PATTERNS = [
    r"\bresolved\b", r"\bdiscontinued\b", r"\bcured\b", r"\bclear\b", r"\brules out\b"
]


class ClinicalFactExtractor:
    """
    Deterministic rule-based clinical fact extractor.
    Scans text for clinical concepts and inspects preceding/surrounding sentence context.
    """

    @staticmethod
    def extract_facts(text: str, note_id: str = "") -> List[ExtractedFact]:
        if not text:
            return []

        facts: List[ExtractedFact] = []
        seen_codes = set()

        # Break text into sentences with start/end character offsets
        sentence_spans = []
        for match in re.finditer(r'[^.!?\n]+[.!?\n]?', text):
            sentence_spans.append((match.group(0), match.start(), match.end()))

        # Scan each sentence for ICD-10 clinical concepts
        for sent_text, sent_start, sent_end in sentence_spans:
            sent_lower = sent_text.lower()

            for concept in ICD10_DICTIONARY:
                code = concept["code"]
                if code in seen_codes:
                    continue  # Deduplicate within same note for principal facts

                # Check if any pattern matches in the sentence
                matched_pattern = None
                matched_str = ""
                for pattern in concept["patterns"]:
                    m = re.search(pattern, sent_lower)
                    if m:
                        matched_pattern = pattern
                        matched_str = m.group(0)
                        break

                if not matched_pattern:
                    continue

                # Inspect sentence context window (50 chars before matched pattern)
                match_index = sent_lower.find(matched_str)
                prefix_context = sent_lower[:match_index]
                full_context = sent_text.strip()

                # 1. Check Negation
                is_negated = False
                for neg in NEGATION_PATTERNS:
                    if re.search(neg, prefix_context):
                        is_negated = True
                        break

                # 2. Check Uncertainty
                is_uncertain = False
                uncertainty_qualifier = None
                for uncert_re, qual in UNCERTAINTY_PATTERNS:
                    if re.search(uncert_re, prefix_context) or re.search(uncert_re, sent_lower):
                        is_uncertain = True
                        uncertainty_qualifier = qual
                        break

                # 3. Check Clinical Status
                clinical_status = "active"
                if is_negated:
                    clinical_status = "inactive"
                else:
                    for res_pat in RESOLVED_PATTERNS:
                        if re.search(res_pat, sent_lower):
                            clinical_status = "resolved"
                            break

                # 4. Check Verification Status
                if is_negated:
                    verification_status = "refuted"
                elif is_uncertain:
                    verification_status = "provisional"
                else:
                    verification_status = "confirmed"

                # 5. Check Present on Admission (POA)
                present_on_admission = "Y"  # Default inpatient assumption
                for poa_no in POA_NO_PATTERNS:
                    if re.search(poa_no, sent_lower):
                        present_on_admission = "N"
                        break

                # 6. Determine Category (Chief Complaint vs Encounter Diagnosis vs Problem List)
                category = concept["category"]
                if "chief complaint" in sent_lower or "reason for admission" in sent_lower:
                    category = "chief-complaint"
                elif "past medical history" in sent_lower or "pmh:" in sent_lower:
                    category = "problem-list-item"

                # Create Condition ID deterministically or UUID
                cond_id = f"COND-{note_id[-8:] if note_id else '101'}-{code.replace('.', '')}"

                fact = ExtractedFact(
                    condition_id=cond_id,
                    display_name=concept["display"],
                    icd10_code=code,
                    category=category,
                    verification_status=verification_status,
                    clinical_status=clinical_status,
                    present_on_admission=present_on_admission,
                    is_negated=is_negated,
                    is_uncertain=is_uncertain,
                    uncertainty_qualifier=uncertainty_qualifier,
                    acuity=concept["acuity"],
                    supporting_text=full_context,
                    start_char=sent_start + match_index,
                    end_char=sent_start + match_index + len(matched_str)
                )

                facts.append(fact)
                seen_codes.add(code)

        return facts
