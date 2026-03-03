from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# =====================================================
#  DB LOADING
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILES = ["uk.json", "us.json"]


def load_db():
    """
    Load multiple country JSON files (uk.json, us.json, etc.) and merge into:
      - countries: list of country objects
      - flat_courses: list of merged entries country+uni+course
    Supports:
      { "countries": [ {...}, {...} ] }
      OR { "code": "UK", "name": "...", "universities": [ ... ] }
    """
    countries = []

    for filename in DATA_FILES:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "countries" in data:
            for c in data["countries"]:
                countries.append(c)

        elif isinstance(data, dict) and data.get("code") and data.get("universities"):
            countries.append(data)

        else:
            print(f"[WARN] {filename} has unexpected format, skipped.")

    if not countries:
        raise ValueError("No valid countries loaded from JSON files.")

    flat_courses = []
    for country in countries:
        c_code = (country.get("code") or "").upper()
        c_name = country.get("name")

        for uni in country.get("universities", []):
            u_name = uni.get("name", "Unknown University")
            city = uni.get("city", "")

            for course in uni.get("courses", []):
                merged = {
                    "country_code": c_code,
                    "country_name": c_name,
                    "country": country,
                    "university_name": u_name,
                    "university": uni,
                    "city": city,
                    "course": course,
                    "course_id": course.get("id"),
                }
                flat_courses.append(merged)

    return {
        "raw": {"countries": countries},
        "countries": countries,
        "flat_courses": flat_courses,
    }


DB = load_db()
COUNTRY_BY_CODE = { (c.get("code") or "").upper(): c for c in DB["countries"] }

# =====================================================
#  HELPERS
# =====================================================

def to_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def to_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def month_from_intake_string(intake_str: str) -> str:
    if not intake_str:
        return ""
    parts = intake_str.strip().split()
    if not parts:
        return ""
    return parts[0][:3].title()

def build_tier_label(tier_band: str):
    mapping = {
        "russell_group_top": "Russell Group / Top UK research university",
        "public_research": "Public research university",
        "teaching_focused": "Teaching-focused / modern university",
        "general_public": "General public university",
        "private": "Private / specialist institution",
        "modern_university": "Modern / teaching-focused university",
    }
    return mapping.get(tier_band, "General university")

def classify_level(cgpa: float, min_cgpa: float):
    """
    Strict academic categorisation:
      SAFE      : cgpa >= min_cgpa + 1.0
      MODERATE  : min_cgpa <= cgpa < min_cgpa + 1.0
      AMBITIOUS : min_cgpa - 0.5 <= cgpa < min_cgpa
      REJECT    : cgpa < min_cgpa - 0.5
    """
    if min_cgpa is None:
        return "unknown"

    diff = cgpa - min_cgpa
    if diff >= 1.0:
        return "safe"
    elif diff >= 0.0:
        return "moderate"
    elif diff >= -0.5:
        return "ambitious"
    else:
        return "reject"

def budget_fit_label(total_cost: float, budget: float):
    if budget <= 0:
        return "unknown"
    if total_cost <= 0.8 * budget:
        return "very_comfortable"
    elif total_cost <= budget:
        return "tight_but_possible"
    else:
        return "over_budget"

def parse_ranking_band_to_score(band: Any) -> float:
    """
    Converts ranking band strings like "60–80" or "50-60" to a 0..1 score.
    Lower rank number => better.
    If missing => neutral 0.5
    """
    if not band:
        return 0.5
    if isinstance(band, (int, float)):
        # if already numeric rank (lower better)
        r = float(band)
        return clamp(1.0 - (r / 300.0), 0.0, 1.0)
    s = str(band).replace("–", "-").replace("—", "-").strip()
    # try "60-80"
    parts = s.split("-")
    try:
        if len(parts) == 2:
            lo = float(parts[0].strip())
            hi = float(parts[1].strip())
            mid = (lo + hi) / 2.0
            return clamp(1.0 - (mid / 300.0), 0.0, 1.0)
        # try single number
        val = float(s)
        return clamp(1.0 - (val / 300.0), 0.0, 1.0)
    except Exception:
        return 0.5

def english_ok_for_course(course: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[bool, bool, str]:
    """
    Returns:
      (ok_now, gap, reason_text)
    """
    proof = (profile.get("english_proof_type") or "").lower()
    score = to_float(profile.get("english_score"), 0)

    min_ielts = course.get("min_ielts_overall")
    min_pte = course.get("min_pte_overall")
    min_duo = course.get("min_duolingo")
    inter_ok = bool(course.get("inter_english_ok", False))

    # No test provided
    if proof in ("none", "", None):
        return (False, True, "No English test provided.")

    if proof == "ielts":
        if min_ielts is None:
            return (True, False, "IELTS accepted (course min not specified).")
        return (score >= float(min_ielts), score < float(min_ielts), f"IELTS needs ≥ {min_ielts}.")

    if proof == "pte":
        if min_pte is None:
            return (True, False, "PTE accepted (course min not specified).")
        return (score >= float(min_pte), score < float(min_pte), f"PTE needs ≥ {min_pte}.")

    if proof == "duolingo":
        if min_duo is None:
            return (True, False, "Duolingo accepted (course min not specified).")
        return (score >= float(min_duo), score < float(min_duo), f"Duolingo needs ≥ {min_duolingo}.")

    if proof in ("inter", "medium"):
        country = COUNTRY_BY_CODE.get((profile.get("country_code") or "").upper(), {}) or {}
        country_allows_inter = bool(country.get("allow_inter_english", False))
        if inter_ok and country_allows_inter:
            return (True, False, "Inter/Medium accepted by course + country policy.")
        return (False, True, "Inter/Medium not accepted for this course/country.")

    # unknown type
    return (False, True, "Unknown English proof type.")

def build_why_country(country: Dict[str, Any]) -> List[str]:
    reasons = []
    for r in (country.get("reasons_to_choose") or [])[:3]:
        reasons.append(r)

    notes = country.get("admission_notes")
    if notes:
        reasons.append(notes)

    visa_rules = country.get("visa_rules") or {}
    work_hrs = visa_rules.get("work_during_studies_hours_per_week")
    if work_hrs:
        reasons.append(f"Can usually work up to {work_hrs} hours/week during studies (confirm latest official rules).")
    psw = visa_rules.get("post_study_work_options")
    if psw:
        reasons.append(f"Post-study work route: {psw}")

    return reasons

def build_why_university(uni: Dict[str, Any]) -> List[str]:
    reasons = []
    for h in (uni.get("highlights") or [])[:3]:
        reasons.append(h)

    city_notes = uni.get("city_notes")
    if isinstance(city_notes, list):
        reasons.extend(city_notes[:2])
    elif city_notes:
        reasons.append(city_notes)

    ranking = uni.get("ranking_band_global")
    if ranking:
        reasons.append(f"Approx global ranking band: {ranking}.")

    return reasons

def build_why_course(course: Dict[str, Any]) -> List[str]:
    reasons = []
    for h in (course.get("course_highlights") or [])[:3]:
        reasons.append(h)

    if course.get("with_placement"):
        reasons.append("Includes placement / internship component (subject to availability).")
    if course.get("is_flagship"):
        reasons.append("Flagship program in this subject area.")

    return reasons

def build_pros(merged: Dict[str, Any]) -> List[str]:
    uni = merged["university"]
    course = merged["course"]
    pros = []
    pros.extend(uni.get("highlights") or [])
    pros.extend(course.get("course_highlights") or [])
    return pros[:8]

def build_cons(merged: Dict[str, Any]) -> List[str]:
    uni = merged["university"]
    course = merged["course"]
    cons = []
    cons.extend(uni.get("cautions") or [])
    cons.extend(course.get("course_cautions") or [])
    if not cons:
        cons.append("No major public red flags; still cross-check recent reviews, outcomes and visa updates.")
    return cons[:8]

# =====================================================
#  AI STYLE SCORING (Weighted)
# =====================================================

def compute_country_policy_weight(country: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Dynamic country policy weight (0..1).
    This is NOT live gov data; it's heuristic using your country JSON fields.
    """
    notes = []
    w = 0.5

    # Visa risk posture (if available at country level)
    visa_rules = country.get("visa_rules") or {}
    if visa_rules.get("post_study_work_options"):
        w += 0.10
        notes.append("Post-study work route available (+).")

    # Inter/Medium policy effect
    proof = (profile.get("english_proof_type") or "").lower()
    if proof in ("inter", "medium"):
        if country.get("allow_inter_english", False):
            w += 0.05
            notes.append("Country sometimes accepts Inter/Medium for admission (+small).")
        else:
            w -= 0.15
            notes.append("Country generally prefers IELTS/PTE/TOEFL (−).")

    # UK/US special baseline
    code = (country.get("code") or "").upper()
    if code == "US":
        w += 0.05
        notes.append("US strong STEM market baseline (+small).")
    if code == "UK":
        w += 0.03
        notes.append("UK 1-year Masters speed baseline (+small).")

    return (clamp(w, 0.0, 1.0), notes)

def compute_fit_score_and_probability(merged: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, int, Dict[str, Any]]:
    """
    Returns:
      fit_score (0..100),
      admission_probability (0..100),
      explainability dict
    """
    country = merged["country"]
    uni = merged["university"]
    course = merged["course"]

    cgpa = to_float(profile.get("cgpa"), 0)
    min_cgpa = to_float(course.get("min_cgpa_india", 0), 0)

    backlogs = to_int(profile.get("backlogs_count"), 0)
    max_backlogs = course.get("max_backlogs")
    max_backlogs = None if max_backlogs is None else to_int(max_backlogs, 0)

    budget = to_float(profile.get("budget_lakhs"), 0)
    tuition = to_float(course.get("tuition_fee_lakhs"), 0)
    living = to_float(course.get("estimated_living_lakhs"), 0)
    extra = to_float(course.get("extra_costs_lakhs"), 0)
    total_cost = tuition + living + extra

    work_ex = to_float(profile.get("work_ex_years"), 0)
    work_req = to_float(course.get("work_exp_required_years", 0), 0)

    # Core checks
    level_band = classify_level(cgpa, min_cgpa)

    english_ok, english_gap, english_reason = english_ok_for_course(course, profile)

    # Ranking score
    rank_global = uni.get("ranking_band_global")
    rank_us = uni.get("ranking_band_us")
    ranking_score = parse_ranking_band_to_score(rank_us or rank_global)  # 0..1

    # Scholarship impact score (0..1)
    typical_sch = to_float(course.get("typical_scholarship_lakhs", 0), 0)
    scholarship_ratio = 0.0
    if total_cost > 0:
        scholarship_ratio = clamp(typical_sch / total_cost, 0.0, 0.35)  # cap huge
    scholarship_score = clamp(scholarship_ratio / 0.35, 0.0, 1.0)

    # Budget score (0..1)
    if budget <= 0 or total_cost <= 0:
        budget_score = 0.5
    else:
        # If total_cost <= budget => good
        if total_cost <= budget:
            # more margin => higher
            margin = (budget - total_cost) / max(budget, 1e-6)
            budget_score = clamp(0.65 + margin, 0.0, 1.0)
        else:
            # over budget => penalize
            over = (total_cost - budget) / max(budget, 1e-6)
            budget_score = clamp(0.55 - over, 0.0, 0.55)

    # CGPA score (0..1) - strict sensitivity so CGPA changes matter
    if min_cgpa <= 0:
        cgpa_score = 0.6
    else:
        diff = cgpa - min_cgpa
        # diff >= +1 => near 1.0; diff=0 => 0.70; diff=-0.5 => 0.40
        cgpa_score = clamp(0.70 + (diff * 0.30), 0.0, 1.0)

    # Backlogs score (0..1)
    if max_backlogs is None:
        backlogs_score = 0.75
    else:
        if backlogs <= max_backlogs:
            # closer to 0 is better
            ratio = (max_backlogs - backlogs) / max(max_backlogs, 1)
            backlogs_score = clamp(0.60 + 0.40 * ratio, 0.0, 1.0)
        else:
            backlogs_score = 0.0

    # Work-ex score (0..1)
    if work_req <= 0:
        workex_score = 0.75 if work_ex >= 0 else 0.7
    else:
        if work_ex >= work_req:
            extra_years = work_ex - work_req
            workex_score = clamp(0.70 + 0.10 * extra_years, 0.70, 1.0)
        else:
            gap = (work_req - work_ex) / max(work_req, 1e-6)
            workex_score = clamp(0.60 - 0.60 * gap, 0.0, 0.60)

    # English score (0..1)
    english_score_component = 0.85 if english_ok else (0.35 if english_gap else 0.6)

    # Country policy weight (0..1)
    country_policy_weight, policy_notes = compute_country_policy_weight(country, profile)

    # Visa risk weight from uni
    visa_risk = (uni.get("visa_risk") or "medium").lower()
    visa_score = {"low": 0.85, "medium": 0.65, "high": 0.40}.get(visa_risk, 0.65)

    # Math/coding strictness risk
    math_required = bool(course.get("math_required", False))
    coding_required = bool(course.get("coding_required", False))
    non_math_bg = bool(profile.get("non_math_background", False))
    skill_score = 0.75
    skill_notes = []
    if math_required and non_math_bg:
        skill_score -= 0.20
        skill_notes.append("Math required + non-math background (penalty).")
    if coding_required:
        skill_score += 0.05
        skill_notes.append("Coding required (ensure projects).")
    skill_score = clamp(skill_score, 0.0, 1.0)

    # Weighted Fit Score (0..100)
    # Keep cgpa weight strong so score changes with CGPA (your key issue)
    weights = {
        "cgpa": 0.30,
        "english": 0.15,
        "budget": 0.12,
        "ranking": 0.10,
        "visa": 0.10,
        "backlogs": 0.08,
        "workex": 0.08,
        "policy": 0.04,
        "skill": 0.03,
    }

    fit_0_1 = (
        cgpa_score * weights["cgpa"]
        + english_score_component * weights["english"]
        + budget_score * weights["budget"]
        + ranking_score * weights["ranking"]
        + visa_score * weights["visa"]
        + backlogs_score * weights["backlogs"]
        + workex_score * weights["workex"]
        + country_policy_weight * weights["policy"]
        + skill_score * weights["skill"]
    )

    # Scholarship impact as a bonus in explainability (not overinflating fit too much)
    # Add up to +5 points max depending on scholarship_score
    scholarship_bonus = int(round(5 * scholarship_score))
    fit_score = int(round(clamp(fit_0_1, 0.0, 1.0) * 100))
    fit_score = int(clamp(fit_score + scholarship_bonus, 0, 100))

    # Admission Probability heuristic (0..100)
    # Start from fit then apply hard penalties for gaps (strictness)
    prob = fit_score

    # CGPA strictness -> if ambitious, cap probability low
    if level_band == "ambitious":
        prob = min(prob, 35)
    elif level_band == "moderate":
        prob = min(prob, 70)

    # English gap => big cap
    if english_gap:
        prob = min(prob, 30)

    # Over budget => cap
    if budget > 0 and total_cost > budget:
        prob = min(prob, 45)

    # Workex gap for MBA etc
    if work_req > 0 and work_ex < work_req:
        prob = min(prob, 25)

    # Uni visa risk high => cap
    if visa_risk == "high":
        prob = min(prob, 40)

    # If any hard invalids (should be filtered earlier mostly)
    if max_backlogs is not None and backlogs > max_backlogs:
        prob = 0

    admission_probability = int(clamp(prob, 0, 100))

    explainability = {
        "weights": weights,
        "components_0_to_1": {
            "cgpa_score": round(cgpa_score, 3),
            "english_score": round(english_score_component, 3),
            "budget_score": round(budget_score, 3),
            "ranking_score": round(ranking_score, 3),
            "visa_score": round(visa_score, 3),
            "backlogs_score": round(backlogs_score, 3),
            "workex_score": round(workex_score, 3),
            "policy_score": round(country_policy_weight, 3),
            "skill_score": round(skill_score, 3),
            "scholarship_score": round(scholarship_score, 3),
        },
        "key_notes": [
            f"CGPA {cgpa} vs min {min_cgpa} → band: {level_band}",
            english_reason,
            f"Budget {budget}L vs cost {total_cost}L",
            f"Visa risk: {visa_risk}",
        ]
        + policy_notes
        + skill_notes,
        "scholarship_bonus_points": scholarship_bonus,
    }

    return fit_score, admission_probability, explainability

# =====================================================
#  RESPONSE BUILDERS
# =====================================================

def build_course_response(merged: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any] | None:
    country = merged["country"]
    uni = merged["university"]
    course = merged["course"]

    cgpa = to_float(profile["cgpa"], 0)
    min_cgpa = to_float(course.get("min_cgpa_india", 0), 0)

    level_band = classify_level(cgpa, min_cgpa)
    if level_band == "reject":
        return None

    tuition = to_float(course.get("tuition_fee_lakhs", 0), 0)
    living = to_float(course.get("estimated_living_lakhs", 0), 0)
    extra = to_float(course.get("extra_costs_lakhs", 0), 0)
    total = tuition + living + extra

    budget = to_float(profile["budget_lakhs"], 0)
    budget_label = budget_fit_label(total, budget)

    english_ok, english_gap, _ = english_ok_for_course(course, profile)

    tier_label = build_tier_label(uni.get("tier_band"))
    intakes = course.get("intakes", []) or []
    intakes_text = " / ".join(intakes) if intakes else "Not specified"

    pros = build_pros(merged)
    cons = build_cons(merged)
    why_country = build_why_country(country)
    why_uni = build_why_university(uni)
    why_course = build_why_course(course)

    english_req = {
        "min_ielts_overall": course.get("min_ielts_overall"),
        "min_pte_overall": course.get("min_pte_overall"),
        "min_duolingo": course.get("min_duolingo"),
        "inter_english_ok": course.get("inter_english_ok", False),
        "country_allows_inter": country.get("allow_inter_english", False),
        "english_ok_now": english_ok,
    }

    fit_score, admission_probability, explainability = compute_fit_score_and_probability(merged, profile)

    advice_parts = []
    if level_band == "safe":
        advice_parts.append("Academically this is a SAFE match.")
    elif level_band == "moderate":
        advice_parts.append("Academically this is a MODERATE match.")
    elif level_band == "ambitious":
        advice_parts.append("Academically this is AMBITIOUS — strong SOP/projects needed.")

    if budget_label == "very_comfortable":
        advice_parts.append("Budget looks comfortable.")
    elif budget_label == "tight_but_possible":
        advice_parts.append("Budget is tight but possible with planning.")
    elif budget_label == "over_budget":
        advice_parts.append("Over budget — need scholarship/loan or lower-cost option.")

    if english_gap:
        advice_parts.append("English requirement gap — IELTS/PTE/Duolingo upgrade strongly recommended.")

    if course.get("math_required") and profile.get("non_math_background"):
        advice_parts.append("Math required — revise stats/maths seriously before this program.")

    if to_float(course.get("work_exp_required_years", 0), 0) > to_float(profile.get("work_ex_years", 0), 0):
        advice_parts.append("Work-ex required — this program may reject without enough experience.")

    short_advice = " ".join(advice_parts)

    return {
        "course_id": course.get("id"),
        "country_code": country.get("code"),
        "country_name": country.get("name"),
        "university_name": uni.get("name", "Unknown University"),
        "city": uni.get("city", ""),
        "course_name": course.get("name"),
        "subject_cluster": course.get("subject_cluster"),
        "level_band": level_band,
        "visa_risk": uni.get("visa_risk"),
        "tier_label": tier_label,

        "tuition_fee_lakhs": tuition,
        "estimated_living_lakhs": living,
        "extra_costs_lakhs": extra,
        "total_first_year_cost_lakhs": total,
        "budget_label": budget_label,

        "intakes": intakes,
        "intakes_text": intakes_text,

        "math_required": course.get("math_required", False),
        "coding_required": course.get("coding_required", False),
        "is_flagship": course.get("is_flagship", False),
        "with_placement": course.get("with_placement", False),
        "typical_scholarship_lakhs": course.get("typical_scholarship_lakhs", 0),

        "english_requirement": english_req,

        # Explainability blocks
        "why_country": why_country,
        "why_university": why_uni,
        "why_course": why_course,
        "pros": pros,
        "cons": cons,

        "short_advice": short_advice,
        "official_course_url": course.get("official_course_url"),

        # ✅ NEW AI FIELDS
        "fit_score": fit_score,
        "admission_probability": admission_probability,
        "ai_explainability": explainability,
    }

def global_advice_from_results(country: Dict[str, Any], profile: Dict[str, Any], course_items: List[Dict[str, Any]]):
    advice = {
        "headline": "",
        "english_advice": "",
        "budget_advice": "",
        "profile_gaps": [],
        "next_steps": [],
    }

    if not course_items:
        advice["headline"] = "No strong matches found with current strict filters."
        advice["next_steps"].append("Try improving IELTS/PTE, increasing budget, or selecting different clusters.")
        advice["next_steps"].append("If CGPA is low, prefer teaching-focused universities and avoid top research-heavy programs.")
        return advice

    # Stronger AI summary:
    avg_fit = sum(c.get("fit_score", 0) for c in course_items) / max(len(course_items), 1)
    best = max(course_items, key=lambda x: x.get("fit_score", 0))

    advice["headline"] = f"Overall average fit score: {int(round(avg_fit))}/100. Best match: {best.get('university_name')} ({best.get('fit_score')}/100)."

    needs_test = (profile.get("english_proof_type") or "") in ("none", "inter", "medium")
    if needs_test:
        advice["english_advice"] = "Taking IELTS/PTE/Duolingo will unlock more options and improve visa confidence."
    else:
        advice["english_advice"] = "Your English proof looks acceptable; still verify course-wise sub-score requirements."

    over_budget_count = sum(1 for c in course_items if c.get("budget_label") == "over_budget")
    if over_budget_count > 0:
        advice["budget_advice"] = "Some options are above your budget — use scholarship/loan plan or target lower-cost cities."
    else:
        advice["budget_advice"] = "Budget looks reasonable for most shown options."

    if any((c.get("ai_explainability", {}).get("components_0_to_1", {}).get("cgpa_score", 1) < 0.55) for c in course_items):
        advice["profile_gaps"].append("CGPA is borderline for some programs — SOP/projects + safer university mix needed.")

    if any((c.get("ai_explainability", {}).get("components_0_to_1", {}).get("english_score", 1) < 0.6) for c in course_items):
        advice["profile_gaps"].append("English readiness is limiting — improve IELTS/PTE for better acceptance odds.")

    if any((c.get("ai_explainability", {}).get("components_0_to_1", {}).get("budget_score", 1) < 0.5) for c in course_items):
        advice["profile_gaps"].append("Budget is tight — scholarships, part-time plan, and cheaper cities are critical.")

    advice["next_steps"].append("Apply mix rule: 2 SAFE + 2 MODERATE + 1 AMBITIOUS (but keep AMBITIOUS probability low).")
    advice["next_steps"].append("Prepare SOP + CV + transcripts + LORs. Cross-check official course pages before paying application fees.")

    country_name = country.get("name")
    if country_name == "United Kingdom":
        advice["next_steps"].append("UK: confirm UKVI latest rules + funds proof; apply early for Sep intake.")
    elif country_name == "United States":
        advice["next_steps"].append("US: confirm GRE/GMAT policy program-wise; plan 8–12 months before intake.")

    return advice

# =====================================================
#  ROUTES
# =====================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Beast Consultancy backend healthy."})

@app.route("/")
def root():
    return jsonify({
        "message": "Beast Consultancy Backend is running.",
        "available_endpoints": [
            "/health",
            "/countries",
            "/courses/<country_code>",
            "/recommend (POST)",
        ]
    })

@app.route("/countries", methods=["GET"])
def get_countries():
    items = []
    for c in DB["countries"]:
        items.append({
            "code": (c.get("code") or "").upper(),
            "name": c.get("name"),
            "flag": c.get("flag", ""),
            "default_currency": c.get("default_currency"),
        })
    return jsonify(items)

@app.route("/courses/<country_code>", methods=["GET"])
def get_courses(country_code):
    country = COUNTRY_BY_CODE.get(country_code.upper())
    if not country:
        return jsonify({"error": "Country not found"}), 404

    clusters = {}
    for uni in country.get("universities", []):
        for course in uni.get("courses", []):
            cluster = course.get("subject_cluster", "other")
            if cluster not in clusters:
                clusters[cluster] = {
                    "subject_cluster": cluster,
                    "display_name": cluster.replace("_", " ").title(),
                    "example_course": course.get("name"),
                    "count": 0,
                }
            clusters[cluster]["count"] += 1

    return jsonify(list(clusters.values()))

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True) or {}

    country_code = (data.get("country_code") or "UK").upper()
    country = COUNTRY_BY_CODE.get(country_code)
    if not country:
        return jsonify({"error": "Invalid or unsupported country_code"}), 400

    profile = {
        "name": data.get("name") or "Student",
        "country_code": country_code,
        "cgpa": to_float(data.get("cgpa", 0), 0),
        "backlogs_count": to_int(data.get("backlogs_count", 0), 0),
        "english_proof_type": (data.get("english_proof_type") or "").lower(),
        "english_score": to_float(data.get("english_score", 0), 0),
        "budget_lakhs": to_float(data.get("budget_lakhs", 0), 0),
        "work_ex_years": to_float(data.get("work_ex_years", 0), 0),
        "non_math_background": bool(data.get("non_math_background", False)),
        "target_intake": data.get("target_intake", ""),
        "intake_month": month_from_intake_string(data.get("target_intake", "")),
    }

    subject_clusters = data.get("subject_clusters") or []
    subject_clusters = [c for c in subject_clusters if c]

    requested_count = to_int(data.get("requested_count", 7), 7)
    requested_count = max(1, min(requested_count, 15))

    cgpa = profile["cgpa"]
    backlogs = profile["backlogs_count"]

    # =================================================
    #   HARD FILTER (STRICT): country + subject + backlogs + CGPA
    # =================================================
    matches = []
    for merged in DB["flat_courses"]:
        if merged["country_code"] != country_code:
            continue

        course = merged["course"]

        # strict cluster filter (frontend already forces at least 1)
        cluster = course.get("subject_cluster", "")
        if subject_clusters and cluster not in subject_clusters:
            continue

        # backlogs filter
        max_backlogs = course.get("max_backlogs")
        if max_backlogs is not None and backlogs > to_int(max_backlogs, 0):
            continue
        if not course.get("accepts_backlog_history", True) and backlogs > 0:
            continue

        # CGPA strictness
        min_cgpa = to_float(course.get("min_cgpa_india", 0), 0)
        level_band = classify_level(cgpa, min_cgpa)

        # Strict reject
        if level_band == "reject":
            continue

        matches.append(merged)

    # =================================================
    #   TRANSFORM + SCORE
    # =================================================
    course_items = []
    for merged in matches:
        item = build_course_response(merged, profile)
        if item:
            course_items.append(item)

    # Sort primarily by Fit Score desc, then probability desc, then cost asc
    course_items.sort(
        key=lambda c: (
            -(c.get("fit_score", 0)),
            -(c.get("admission_probability", 0)),
            c.get("total_first_year_cost_lakhs", 10**9),
        )
    )

    # Keep at least 1 ambitious if exists (but must be low prob & explainable)
    ambitious_pool = [c for c in course_items if c.get("level_band") == "ambitious"]
    top = course_items[:requested_count]

    if not any(c.get("level_band") == "ambitious" for c in top) and ambitious_pool:
        dream = ambitious_pool[0]
        # Ensure ambitious shown is visibly low probability (trust)
        dream["admission_probability"] = min(dream.get("admission_probability", 35), 30)
        top.append(dream)

    advice = global_advice_from_results(country, profile, top)

    response = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "student_profile": profile,
        "country": {
            "code": country.get("code"),
            "name": country.get("name"),
            "flag": country.get("flag", ""),
        },
        "stats": {
            "total_matches_before_limit": len(matches),
            "total_shown": len(top),
            "safe_count": sum(1 for c in top if c.get("level_band") == "safe"),
            "moderate_count": sum(1 for c in top if c.get("level_band") == "moderate"),
            "ambitious_count": sum(1 for c in top if c.get("level_band") == "ambitious"),
        },
        "recommendations": top,
        "global_advice": advice,
    }

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)