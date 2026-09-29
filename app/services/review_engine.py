"""
Decoupled Principal Diagnosis Review Engine.
Retrieves FHIR resources & original note STRICTLY via HTTP APIs.
Applies FY 2026 ICD-10-CM Section II Guidelines for Principal Diagnosis selection.
"""

import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from app.schemas import ReviewRequest, ReviewResult, CompetingPossibility


class PrincipalDiagnosisReviewEngine:
    """
    Decoupled Review Engine that consumes FHIR REST APIs over HTTP.
    Evaluates FY 2026 ICD-10-CM Coding Guidelines (Section II.A, II.B, II.C, II.D, II.G).
    """

    @staticmethod
    def _fetch_json_over_http(url: str) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers={"Accept": "application/fhir+json, application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = response.read().decode("utf-8")
                    return json.loads(data)
                else:
                    raise ValueError(f"HTTP GET {url} returned status {response.status}")
        except urllib.error.HTTPError as e:
            raise ValueError(f"HTTP GET {url} failed with status {e.code}: {e.reason}")
        except Exception as e:
            raise ValueError(f"Failed to fetch {url} over HTTP: {str(e)}")

    @staticmethod
    def evaluate_encounter(request: ReviewRequest) -> ReviewResult:
        base_url = request.fhir_api_base_url
        enc_id = request.encounter_id

        # 1. Fetch Encounter over HTTP
        enc_url = f"{base_url}/fhir/Encounter/{enc_id}"
        encounter_data = PrincipalDiagnosisReviewEngine._fetch_json_over_http(enc_url)
        if not encounter_data:
            return ReviewResult(
                encounter_id=enc_id,
                recommendation_status="UNSUPPORTED",
                next_action="Verify encounter ID and ensure note has been ingested.",
                missing_information=["Encounter resource not found via FHIR API"],
            )

        # 2. Fetch Conditions by encounter over HTTP
        cond_url = f"{base_url}/fhir/Condition?encounter={enc_id}"
        condition_bundle = PrincipalDiagnosisReviewEngine._fetch_json_over_http(cond_url)
        conditions = []
        if condition_bundle.get("resourceType") == "Bundle":
            for entry in condition_bundle.get("entry", []):
                res = entry.get("resource", {})
                if res.get("resourceType") == "Condition":
                    conditions.append(res)
        elif isinstance(condition_bundle, list):
            conditions = condition_bundle

        # 3. Fetch DocumentReference & Binary over HTTP
        docref_url = f"{base_url}/fhir/DocumentReference?encounter={enc_id}"
        docref_bundle = PrincipalDiagnosisReviewEngine._fetch_json_over_http(docref_url)
        note_text = ""
        docref_entries = docref_bundle.get("entry", []) if docref_bundle.get("resourceType") == "Bundle" else []
        if docref_entries:
            docref = docref_entries[0].get("resource", {})
            contents = docref.get("content", [])
            if contents:
                binary_url_rel = contents[0].get("attachment", {}).get("url", "")
                binary_id = binary_url_rel.replace("Binary/", "")
                if binary_id:
                    binary_url = f"{base_url}/fhir/Binary/{binary_id}"
                    binary_data = PrincipalDiagnosisReviewEngine._fetch_json_over_http(binary_url)
                    b64_data = binary_data.get("data", "")
                    if b64_data:
                        try:
                            note_text = base64.b64decode(b64_data).decode("utf-8")
                        except Exception:
                            note_text = b64_data

        if not conditions:
            return ReviewResult(
                encounter_id=enc_id,
                recommendation_status="UNSUPPORTED",
                next_action="Perform clinical documentation review; no active conditions extracted.",
                missing_information=["No Condition resources returned for encounter"],
            )

        # Parse conditions into internal review structures
        parsed_candidates = []
        for cond in conditions:
            code_obj = cond.get("code", {}).get("coding", [{}])[0]
            icd_code = code_obj.get("code", "")
            display = code_obj.get("display", cond.get("code", {}).get("text", ""))
            ver_status = cond.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "confirmed")
            clin_status = cond.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active")
            cat = cond.get("category", [{}])[0].get("coding", [{}])[0].get("code", "encounter-diagnosis")

            poa = "Y"
            supporting_text = ""
            acuity = "unspecified"
            uncertainty_qualifier = None

            for ext in cond.get("extension", []):
                url = ext.get("url", "")
                if "presentOnAdmission" in url:
                    poa = ext.get("valueCode", "Y")
                elif "supportingText" in url:
                    supporting_text = ext.get("valueString", "")
                elif "acuity" in url:
                    acuity = ext.get("valueString", "unspecified")
                elif "uncertaintyQualifier" in url:
                    uncertainty_qualifier = ext.get("valueString")

            # Filter out refuted / inactive conditions
            if ver_status == "refuted" or clin_status == "inactive":
                continue

            parsed_candidates.append({
                "condition_id": cond.get("id"),
                "icd10_code": icd_code,
                "display_name": display,
                "verification_status": ver_status,
                "clinical_status": clin_status,
                "category": cat,
                "poa": poa,
                "acuity": acuity,
                "supporting_text": supporting_text,
                "uncertainty_qualifier": uncertainty_qualifier,
            })

        # Apply FY 2026 ICD-10-CM Coding Guidelines
        guideline_references = []
        assumptions = []
        missing_info = []
        competing = []
        supporting_passages = []

        # Identify Candidate Categories
        symptom_codes = {"R07.9", "R06.02", "R10.9", "R50.9"}
        sepsis_codes = {"A41.9", "R65.20", "R65.21"}
        acute_organ_or_systemic = {"J96.00", "N17.9", "I50.21", "J44.1", "K92.2", "K57.32", "I63.9", "K35.80", "J18.9", "N39.0", "I21.9", "K85.90"}

        # Rule II.A: Symptoms vs Definitive Diagnoses
        # Separate symptoms from definitive diagnoses
        definitive = [c for c in parsed_candidates if c["icd10_code"] not in symptom_codes]
        symptoms = [c for c in parsed_candidates if c["icd10_code"] in symptom_codes]

        if symptoms and definitive:
            guideline_references.append("FY 2026 ICD-10-CM Guidelines Section II.A: Codes for symptoms, signs, and ill-defined conditions are not to be used as principal diagnosis when a related definitive diagnosis has been established.")
            for s in symptoms:
                competing.append(CompetingPossibility(
                    icd10_code=s["icd10_code"],
                    display_name=s["display_name"],
                    verification_status=s["verification_status"],
                    exclusion_reason="Subordinated under Section II.A as a symptom accounted for by definitive diagnosis."
                ).to_dict())

        # Evaluate Candidates
        primary_candidates = definitive if definitive else parsed_candidates

        # Rule II.B: Sepsis vs Localized Infection
        has_sepsis = any(c["icd10_code"] in sepsis_codes for c in primary_candidates)
        has_localized = any(c["icd10_code"] in {"J18.9", "N39.0"} for c in primary_candidates)

        if has_sepsis and has_localized:
            guideline_references.append("FY 2026 ICD-10-CM Guidelines Section II.B: Sepsis is sequenced as principal diagnosis when secondary to a localized infection (e.g. pneumonia or UTI) present on admission.")
            assumptions.append("Assumed systemic sepsis was chief driver of acute inpatient stay and resource utilization.")

        # Rule II.D: Contrasting / Unconfirmed Diagnoses (e.g. Appendicitis vs Diverticulitis equal uncertainty)
        provisional_candidates = [c for c in primary_candidates if c["verification_status"] == "provisional"]
        if len(provisional_candidates) >= 2:
            guideline_references.append("FY 2026 ICD-10-CM Guidelines Section II.D: Two or more comparative or contrasting conditions documented at discharge remain unconfirmed; clinical clarification required.")
            
            for c in provisional_candidates:
                if c["supporting_text"]:
                    supporting_passages.append(c["supporting_text"])
                competing.append(CompetingPossibility(
                    icd10_code=c["icd10_code"],
                    display_name=c["display_name"],
                    verification_status=c["verification_status"],
                    exclusion_reason="Equally probable unconfirmed candidate requiring physician query."
                ).to_dict())

            return ReviewResult(
                encounter_id=enc_id,
                recommendation_status="CLARIFICATION_NEEDED",
                recommended_condition=None,
                supporting_passages=list(set(supporting_passages)),
                guideline_references=guideline_references,
                competing_possibilities=competing,
                assumptions=["Both diagnoses documented with equal uncertainty at discharge."],
                missing_information=["Attending physician clarification or pathology/imaging confirmation."],
                next_action="Submit CDI physician query to clarify principal diagnosis between competing provisional conditions.",
            )

        # Rule II.G: Uncertain Diagnosis at Discharge in Inpatient Setting
        for c in primary_candidates:
            if c["verification_status"] == "provisional":
                guideline_references.append("FY 2026 ICD-10-CM Guidelines Section II.G: Inpatient uncertain diagnosis documented at discharge ('probable', 'suspected', 'likely') is coded as if established.")
                assumptions.append(f"Coded {c['display_name']} ({c['icd10_code']}) as established per Section II.G inpatient guidelines.")

        # Selection Algorithm for Principal Diagnosis
        # Priority:
        # 1. Sepsis (if present and POA=Y)
        # 2. Acute Organ Dysfunction / Acute Condition with POA=Y
        # 3. Encounter Diagnosis with POA=Y
        # 4. Other acute conditions

        def score_candidate(c: Dict[str, Any]) -> int:
            score = 0
            code = c["icd10_code"]
            if code in sepsis_codes:
                score += 100
            elif code in acute_organ_or_systemic:
                score += 80
            
            if c["poa"] == "Y":
                score += 40
            if c["acuity"] in ["acute", "acute-on-chronic"]:
                score += 30
            if c["category"] in ["encounter-diagnosis", "chief-complaint"]:
                score += 20
            return score

        sorted_candidates = sorted(primary_candidates, key=score_candidate, reverse=True)
        winner = sorted_candidates[0]

        # Gather supporting passages
        if winner["supporting_text"]:
            supporting_passages.append(winner["supporting_text"])

        # Record competing possibilities
        for c in sorted_candidates[1:]:
            if c["supporting_text"]:
                supporting_passages.append(c["supporting_text"])
            competing.append(CompetingPossibility(
                icd10_code=c["icd10_code"],
                display_name=c["display_name"],
                verification_status=c["verification_status"],
                exclusion_reason=f"Sequenced after {winner['display_name']} based on acuity, POA status, and ICD-10-CM Section II guidelines."
            ).to_dict())

        if not guideline_references:
            guideline_references.append("FY 2026 ICD-10-CM Guidelines Section II: Selection of Principal Diagnosis (chiefly responsible for occasioning admission after study).")

        recommended_obj = {
            "condition_id": winner["condition_id"],
            "icd10_code": winner["icd10_code"],
            "display_name": winner["display_name"],
            "verification_status": winner["verification_status"],
            "acuity": winner["acuity"],
            "present_on_admission": winner["poa"],
        }

        # Deduplicate passages
        clean_passages = list(dict.fromkeys(supporting_passages))

        return ReviewResult(
            encounter_id=enc_id,
            recommendation_status="SUPPORTED",
            recommended_condition=recommended_obj,
            supporting_passages=clean_passages,
            guideline_references=list(dict.fromkeys(guideline_references)),
            competing_possibilities=competing,
            assumptions=assumptions if assumptions else ["Condition established after study as chiefly responsible for inpatient admission."],
            missing_information=missing_info if missing_info else ["No critical documentation gaps identified."],
            next_action=f"Approve draft recommendation: assign {winner['icd10_code']} ({winner['display_name']}) as principal diagnosis.",
        )
