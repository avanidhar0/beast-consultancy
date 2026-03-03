from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# =====================================================
#  DB LOADING
# =====================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# We will load from multiple JSONs: uk.json, us.json, etc.
DATA_FILES = ["uk.json", "us.json"]


def load_db():
    """
    Load multiple country JSON files (uk.json, us.json, etc.) and merge into:
      - a single list: countries
      - a flat list of all course entries: flat_courses
    Each JSON file can be either:
      { "countries": [ {...}, {...} ] }
    OR
      { "code": "UK", "name": "...", "universities": [ ... ] }
    """
    countries = []

    for filename in DATA_FILES:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Case 1: root has "countries": [...]
        if isinstance(data, dict) and "countries" in data:
            for c in data["countries"]:
                countries.append(c)

        # Case 2: single country object at root
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
COUNTRY_BY_CODE = {((c.get("code") or "").upper()): c for c in DB["countries"] if c.get("code")}


# =====================================================
#  SMALL HELPERS
# =====================================================

def clamp01(x: float) -> float:
    if x is None:
        return 0.0
    try:
        x = float(x)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, x))


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


def month_from_intake_string(intake_str: str) -> str:
    """
    "sep 2026" -> "Sep"
    "Jan 2027" -> "Jan"
    """
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
        "modern_university": "Modern / teaching-focused university",
        "general_public": "General public university",
        "private": "Private / specialist institution",
    }
    return mapping.get(tier_band, "General university")


def classify_level(cgpa, min_cgpa):
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


def budget_fit_label(total_cost, budget):
    if budget <= 0:
        return "unknown"
    if total_cost <= 0.8 * budget:
        return "very_comfortable"
    elif total_cost <= budget:
        return "tight_but_possible"
    else:
        return "over_budget"


# =====================================================
#  ENGLISH CHECK
# =====================================================

def english_ok_for_course(course, profile):
    """
    Returns:
      english_ok_now (bool),
      english_gap (bool),
      waiver_possible (bool)
    """
    proof = (profile.get("english_proof_type") or "").lower()
    score = safe_float(profile.get("english_score"), 0)

    min_ielts = course.get("min_ielts_overall")
    min_pte = course.get("min_pte_overall")
    min_duo = course.get("min_duolingo")
    inter_ok = bool(course.get("inter_english_ok", False))

    country = COUNTRY_BY_CODE.get((profile.get("country_code") or "").upper(), {}) or {}
    country_allows_inter = bool(country.get("allow_inter_english", False))

    # No test provided
    if proof in ("none", None, ""):
        return False, True, False

    if proof == "ielts":
        if min_ielts is None:
            return True, False, False
        return score >= float(min_ielts), score < float(min_ielts), False

    if proof == "pte":
        if min_pte is None:
            return True, False, False
        return score >= float(min_pte), score < float(min_pte), False

    if proof == "duolingo":
        if min_duo is None:
            return True, False, False
        return score >= float(min_duo), score < float(min_duo), False

    if proof in ("inter", "medium"):
        waiver_possible = inter_ok and country_allows_inter
        if waiver_possible:
            # waiver possible, but still weaker for visa/strict unis -> not a full "ok" globally
            return True, False, True
        return False, True, False

    # unknown type
    return False, True, False


# =====================================================
#  A-Z EXPLAINABILITY BUILDERS (short, not spam)
# =====================================================

def build_why_country(country):
    reasons = []

    # main reasons (top 3)
    for r in (country.get("reasons_to_choose") or [])[:3]:
        reasons.append(r)

    notes = country.get("admission_notes")
    if notes:
        reasons.append(notes)

    visa_rules = country.get("visa_rules") or {}
    work_hrs = visa_rules.get("work_during_studies_hours_per_week")
    if work_hrs:
        reasons.append(f"Can usually work up to {work_hrs} hours/week during studies (verify latest official rules).")
    psw = visa_rules.get("post_study_work_options")
    if psw:
        reasons.append(f"Post-study work route: {psw}")

    return reasons


def build_why_university(uni):
    reasons = []
    for h in (uni.get("highlights") or [])[:3]:
        reasons.append(h)

    city_notes = uni.get("city_notes")
    if isinstance(city_notes, list):
        for n in city_notes[:2]:
            reasons.append(str(n))
    elif isinstance(city_notes, str) and city_notes.strip():
        reasons.append(city_notes.strip())

    ranking = uni.get("ranking_band_global")
    if ranking:
        reasons.append(f"Approx global ranking band: {ranking}.")

    return reasons


def build_why_course(course):
    reasons = []
    for h in (course.get("course_highlights") or [])[:3]:
        reasons.append(h)

    if course.get("with_placement"):
        reasons.append("Includes placement / internship component (subject to availability).")

    if course.get("is_flagship"):
        reasons.append("Flagship program of the university in this subject area.")

    return reasons


def build_pros(merged):
    uni = merged["university"]
    course = merged["course"]
    pros = []
    pros.extend(uni.get("highlights") or [])
    pros.extend(course.get("course_highlights") or [])
    return [str(x) for x in pros][:8]


def build_cons(merged):
    uni = merged["university"]
    course = merged["course"]
    cons = []
    cons.extend(uni.get("cautions") or [])
    cons.extend(course.get("course_cautions") or [])
    if not cons:
        cons.append("No major public red flags, but always cross-check recent outcomes, reviews and visa updates.")
    return [str(x) for x in cons][:8]


# =====================================================
#  AI-STYLE SCORING (weighted, explainable)
# =====================================================

DEFAULT_WEIGHTS = {
    "cgpa": 0.30,
    "english": 0.15,
    "budget": 0.12,
    "visa": 0.10,
    "ranking": 0.10,
    "backlogs": 0.08,
    "workex": 0.08,
    "policy": 0.04,
    "skill": 0.03,
}


def compute_ranking_score(uni, course):
    """
    0..1 ranking score.
    Priority: explicit ranking band -> tier fallback.
    """
    band = uni.get("ranking_band_global")
    if isinstance(band, str) and band.strip():
        # crude parsing like "60–80", "100-150"
        digits = []
        for ch in band:
            if ch.isdigit():
                digits.append(ch)
            elif digits and ch in ("–", "-", " "):
                digits.append(",")
        s = "".join(digits).replace(",,", ",").strip(",")
        parts = [p for p in s.split(",") if p]
        nums = []
        for p in parts:
            try:
                nums.append(int(p))
            except Exception:
                pass
        if nums:
            # lower rank number = better
            r = min(nums)
            if r <= 50:
                return 1.0
            if r <= 100:
                return 0.85
            if r <= 200:
                return 0.70
            if r <= 400:
                return 0.55
            return 0.45

    # fallback by tier_band
    tier = (uni.get("tier_band") or "").lower()
    if tier in ("russell_group_top",):
        return 0.90
    if tier in ("public_research",):
        return 0.75
    if tier in ("teaching_focused", "modern_university"):
        return 0.50
    if tier in ("general_public",):
        return 0.45
    return 0.40


def compute_policy_score(country, course, profile):
    """
    tiny tie-breaker (0..1):
    - UK: 1-year masters speed helps small.
    - inter/medium english acceptance helps if user has it.
    """
    code = (country.get("code") or "").upper()
    proof = (profile.get("english_proof_type") or "").lower()

    score = 0.50  # neutral baseline
    if code == "UK":
        score += 0.05  # fast 1-year typical benefit
    if code == "US":
        score += 0.03  # strong STEM + OPT narrative but expensive

    # inter/medium policy advantage only if user uses it and course+country allow
    if proof in ("inter", "medium"):
        inter_ok = bool(course.get("inter_english_ok", False))
        country_allows = bool(country.get("allow_inter_english", False))
        if inter_ok and country_allows:
            score += 0.06
        else:
            score -= 0.10

    return clamp01(score)


def compute_visa_score(uni):
    risk = (uni.get("visa_risk") or "").lower()
    if risk == "low":
        return 0.85
    if risk == "medium":
        return 0.65
    if risk == "high":
        return 0.40
    return 0.60


def compute_skill_score(course, profile):
    """
    0..1: penalize mismatch: math_required + non_math_background
    """
    non_math = bool(profile.get("non_math_background", False))
    math_req = bool(course.get("math_required", False))
    coding_req = bool(course.get("coding_required", False))

    score = 0.80
    if math_req and non_math:
        score -= 0.25
    if coding_req and non_math:
        score -= 0.10
    return clamp01(score)


def compute_workex_score(course, profile):
    """
    0..1 based on meeting required years.
    If course requires 2 years and user has 0 => very low.
    """
    required = safe_float(course.get("work_exp_required_years", 0), 0)
    have = safe_float(profile.get("work_ex_years", 0), 0)

    if required <= 0:
        return 0.75  # neutral advantage for fresher-friendly courses

    if have >= required:
        return 0.90

    # partial
    ratio = have / required if required > 0 else 0.0
    return clamp01(0.15 + 0.70 * ratio)  # 0y => 0.15


def compute_backlogs_score(course, profile):
    max_b = course.get("max_backlogs")
    backlogs = safe_int(profile.get("backlogs_count", 0), 0)

    if max_b is None:
        return 0.80
    max_b = safe_int(max_b, 0)
    if max_b <= 0:
        return 1.0 if backlogs == 0 else 0.0

    if backlogs <= 0:
        return 1.0

    if backlogs > max_b:
        return 0.0

    # closer to 0 is better
    return clamp01(1.0 - (backlogs / max_b) * 0.70)


def compute_budget_score(total_cost, budget, scholarship_lakhs=0.0):
    """
    budget score uses effective cost after scholarship.
    """
    budget = safe_float(budget, 0.0)
    total_cost = safe_float(total_cost, 0.0)
    scholarship_lakhs = max(0.0, safe_float(scholarship_lakhs, 0.0))

    effective = max(0.0, total_cost - scholarship_lakhs)

    if budget <= 0:
        return 0.50

    ratio = effective / budget  # <=1 good
    if ratio <= 0.65:
        return 1.0
    if ratio <= 0.85:
        return 0.85
    if ratio <= 1.0:
        return 0.70
    if ratio <= 1.15:
        return 0.45
    return 0.25


def compute_cgpa_score(cgpa, min_cgpa):
    """
    0..1, but strict banding supports explainability.
    """
    cgpa = safe_float(cgpa, 0.0)
    min_cgpa = safe_float(min_cgpa, 0.0)

    band = classify_level(cgpa, min_cgpa)
    if band == "safe":
        return 1.0
    if band == "moderate":
        return 0.80
    if band == "ambitious":
        return 0.55
    if band == "reject":
        return 0.0
    return 0.60


def compute_english_score_component(course, profile, english_ok_now, english_gap, waiver_possible):
    """
    0..1:
    - meets requirement => high
    - waiver (inter/medium accepted) => medium-high but not perfect
    - gap => low
    """
    proof = (profile.get("english_proof_type") or "").lower()

    if english_ok_now and not english_gap:
        return 0.85 if proof in ("ielts", "pte", "duolingo") else 0.75

    if waiver_possible:
        return 0.70

    return 0.25


def scholarship_bonus_points(typical_scholarship_lakhs):
    """
    convert scholarship to small bonus points (0..3)
    """
    s = safe_float(typical_scholarship_lakhs, 0.0)
    if s >= 5:
        return 3
    if s >= 3:
        return 2
    if s >= 1:
        return 1
    return 0


def compute_fit_and_probability(merged, profile):
    """
    Returns:
      fit_score (0..100),
      admission_probability (0..100),
      explainability dict,
      strict_reject (bool),
      reason (optional)
    """
    country = merged["country"]
    uni = merged["university"]
    course = merged["course"]

    cgpa = safe_float(profile.get("cgpa", 0), 0)
    backlogs = safe_int(profile.get("backlogs_count", 0), 0)
    budget = safe_float(profile.get("budget_lakhs", 0), 0)

    min_cgpa = safe_float(course.get("min_cgpa_india", 0) or 0, 0)
    level_band = classify_level(cgpa, min_cgpa)

    # STRICT REJECTION 1: CGPA too low
    if level_band == "reject":
        return 0, 0, {"reject_reason": "CGPA below minimum threshold (strict reject)."}, True, "cgpa_reject"

    # STRICT REJECTION 2: backlogs beyond max
    max_backlogs = course.get("max_backlogs")
    if max_backlogs is not None:
        if backlogs > safe_int(max_backlogs, 0):
            return 0, 0, {"reject_reason": "Backlogs exceed course maximum (strict reject)."}, True, "backlogs_reject"

    # Tuition + living + extra
    tuition = safe_float(course.get("tuition_fee_lakhs", 0) or 0, 0)
    living = safe_float(course.get("estimated_living_lakhs", 0) or 0, 0)
    extra = safe_float(course.get("extra_costs_lakhs", 0) or 0, 0)
    total = tuition + living + extra

    # English
    english_ok_now, english_gap, waiver_possible = english_ok_for_course(course, profile)

    # We do NOT strict reject for missing workex; we show very low probability for MBA etc.
    required_workex = safe_float(course.get("work_exp_required_years", 0), 0)
    have_workex = safe_float(profile.get("work_ex_years", 0), 0)
    workex_missing = required_workex > 0 and have_workex < required_workex

    # scholarship
    typical_sch = safe_float(course.get("typical_scholarship_lakhs", 0) or 0, 0)
    sch_bonus = scholarship_bonus_points(typical_sch)

    # components (0..1)
    comp = {}
    comp["cgpa_score"] = compute_cgpa_score(cgpa, min_cgpa)
    comp["backlogs_score"] = compute_backlogs_score(course, profile)
    comp["budget_score"] = compute_budget_score(total, budget, typical_sch)
    comp["english_score"] = compute_english_score_component(course, profile, english_ok_now, english_gap, waiver_possible)
    comp["visa_score"] = compute_visa_score(uni)
    comp["ranking_score"] = compute_ranking_score(uni, course)
    comp["policy_score"] = compute_policy_score(country, course, profile)
    comp["skill_score"] = compute_skill_score(course, profile)
    comp["workex_score"] = compute_workex_score(course, profile)

    # weighted fit score
    weights = DEFAULT_WEIGHTS.copy()

    fit_0_to_1 = 0.0
    for k, w in weights.items():
        # mapping: weight keys to comp keys
        ck = f"{k}_score" if k not in ("visa", "ranking", "policy", "skill", "workex", "backlogs", "budget", "cgpa", "english") else f"{k}_score"
        v = comp.get(ck, 0.0)
        fit_0_to_1 += (w * v)

    # scholarship small bonus (points, not huge)
    fit_points = int(round(fit_0_to_1 * 100))
    fit_points = min(100, max(0, fit_points + sch_bonus))

    # Admission probability heuristic:
    # Start from fit, then apply strict penalties.
    prob = fit_points

    # penalties/limits
    key_notes = []

    key_notes.append(f"CGPA {cgpa} vs min {min_cgpa} → band: {level_band}")

    if english_gap and not waiver_possible:
        prob -= 25
        key_notes.append("English requirement not met → heavy penalty.")
    elif waiver_possible:
        prob -= 10
        key_notes.append("English waiver possible (Inter/Medium accepted) → still weaker for visa/strict unis.")

    if level_band == "ambitious":
        prob -= 18
        key_notes.append("Ambitious CGPA band → probability reduced.")

    # workex rule: if required but missing -> cap at 30
    if workex_missing:
        prob = min(prob, 30)
        key_notes.append(f"Work-ex required {required_workex}y but you have {have_workex}y → capped ≤ 30%.")

    # visa risk penalty
    visa_risk = (uni.get("visa_risk") or "").lower()
    if visa_risk == "high":
        prob -= 15
        key_notes.append("Visa risk high → penalty.")

    # budget severe penalty if over budget by a lot (effective cost > 115% of budget)
    effective_cost = max(0.0, total - typical_sch)
    if budget > 0 and (effective_cost / budget) > 1.15:
        prob -= 15
        key_notes.append("Cost significantly over budget → penalty.")

    # coding required note
    if course.get("coding_required"):
        key_notes.append("Coding required (ensure projects).")
    if course.get("math_required") and profile.get("non_math_background"):
        key_notes.append("Math required but non-math background → prepare strongly.")

    prob = max(0, min(95, int(round(prob))))  # keep realistic, never 100%

    explain = {
        "weights": weights,
        "components_0_to_1": {
            "cgpa_score": round(comp["cgpa_score"], 3),
            "english_score": round(comp["english_score"], 3),
            "budget_score": round(comp["budget_score"], 3),
            "visa_score": round(comp["visa_score"], 3),
            "ranking_score": round(comp["ranking_score"], 3),
            "backlogs_score": round(comp["backlogs_score"], 3),
            "workex_score": round(comp["workex_score"], 3),
            "policy_score": round(comp["policy_score"], 3),
            "skill_score": round(comp["skill_score"], 3),
            "scholarship_score": round(clamp01(typical_sch / 10.0), 3),  # normalized for display only
        },
        "scholarship_bonus_points": sch_bonus,
        "key_notes": key_notes[:8],
    }

    return fit_points, prob, explain, False, None


# =====================================================
#  COURSE RESPONSE BUILDER (includes fit + probability)
# =====================================================

def build_course_response(merged, profile):
    country = merged["country"]
    uni = merged["university"]
    course = merged["course"]

    # --- strict scoring + explainability ---
    fit_score, admission_probability, explain, strict_reject, _reason = compute_fit_and_probability(merged, profile)
    if strict_reject:
        return None

    cgpa = safe_float(profile.get("cgpa", 0), 0)
    min_cgpa = safe_float(course.get("min_cgpa_india", 0) or 0, 0)
    level_band = classify_level(cgpa, min_cgpa)

    # --- cost ---
    tuition = safe_float(course.get("tuition_fee_lakhs", 0) or 0, 0)
    living = safe_float(course.get("estimated_living_lakhs", 0) or 0, 0)
    extra = safe_float(course.get("extra_costs_lakhs", 0) or 0, 0)
    total = tuition + living + extra

    budget = safe_float(profile.get("budget_lakhs", 0), 0)
    budget_label = budget_fit_label(total, budget)

    # --- English ---
    english_ok, english_gap, waiver_possible = english_ok_for_course(course, profile)

    # --- labels / text ---
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
        "inter_english_ok": bool(course.get("inter_english_ok", False)),
        "country_allows_inter": bool(country.get("allow_inter_english", False)),
        "english_ok_now": english_ok,
    }

    advice_parts = []

    if level_band == "safe":
        advice_parts.append("Academically this is a SAFE match.")
    elif level_band == "moderate":
        advice_parts.append("Academically this is a MODERATE match.")
    elif level_band == "ambitious":
        advice_parts.append("This is an AMBITIOUS option. Strong SOP/projects required.")

    if budget_label == "very_comfortable":
        advice_parts.append("Budget looks comfortable.")
    elif budget_label == "tight_but_possible":
        advice_parts.append("Budget is tight but possible; manage expenses carefully.")
    elif budget_label == "over_budget":
        advice_parts.append("This is above your stated budget; consider scholarship/loan or cheaper cities.")

    if english_gap and not waiver_possible:
        advice_parts.append("English requirement not met; probability reduced until you improve the score.")
    elif waiver_possible:
        advice_parts.append("English waiver possible (Inter/Medium) but IELTS/PTE is safer for visa and more options.")

    required_workex = safe_float(course.get("work_exp_required_years", 0), 0)
    have_workex = safe_float(profile.get("work_ex_years", 0), 0)
    if required_workex > 0 and have_workex < required_workex:
        advice_parts.append(f"Work-ex required ({required_workex}y). Your current work-ex is {have_workex}y → low probability.")

    short_advice = " ".join(advice_parts)

    return {
        "course_id": course.get("id"),
        "country_code": (country.get("code") or "").upper(),
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

        "math_required": bool(course.get("math_required", False)),
        "coding_required": bool(course.get("coding_required", False)),
        "is_flagship": bool(course.get("is_flagship", False)),
        "with_placement": bool(course.get("with_placement", False)),
        "typical_scholarship_lakhs": safe_float(course.get("typical_scholarship_lakhs", 0) or 0, 0),

        "english_requirement": english_req,
        "why_country": why_country,
        "why_university": why_uni,
        "why_course": why_course,
        "pros": pros,
        "cons": cons,
        "short_advice": short_advice,
        "official_course_url": course.get("official_course_url"),

        # ✅ AI focus outputs
        "fit_score": int(fit_score),
        "admission_probability": int(admission_probability),
        "ai_explainability": explain,
    }


def global_advice_from_results(country, profile, course_items):
    advice = {
        "headline": "",
        "english_advice": "",
        "budget_advice": "",
        "profile_gaps": [],
        "next_steps": [],
    }

    if not course_items:
        advice["headline"] = "No strong matches found with strict filters."
        advice["next_steps"].append("Increase CGPA target match (or choose more flexible universities), improve English, or adjust budget.")
        return advice

    # headline using fit score
    avg_fit = int(round(sum(c.get("fit_score", 0) for c in course_items) / max(1, len(course_items))))
    best = max(course_items, key=lambda x: x.get("fit_score", 0))
    advice["headline"] = f"Overall average fit score: {avg_fit}/100. Best match: {best.get('university_name')} ({best.get('fit_score')}/100)."

    proof = (profile.get("english_proof_type") or "").lower()
    if proof in ("none", "inter", "medium"):
        advice["english_advice"] = "IELTS/PTE/Duolingo will open more universities and strengthens visa, even if some accept Inter/Medium."
    else:
        advice["english_advice"] = "Your English proof looks acceptable; still verify course-wise sub-score requirements."

    # budget note
    over = sum(1 for c in course_items if c.get("budget_label") == "over_budget")
    if over:
        advice["budget_advice"] = "Some options are above your budget. Consider scholarship/loan, cheaper cities, or reduce cost targets."
    else:
        advice["budget_advice"] = "Budget looks reasonable for most shown options."

    # next steps
    advice["next_steps"].append("Apply mix rule: 2 SAFE + 2 MODERATE + 1 AMBITIOUS (but keep AMBITIOUS probability low).")
    advice["next_steps"].append("Prepare SOP + CV + transcripts + LORs. Cross-check official course pages before paying application fees.")
    if (country.get("code") or "").upper() == "UK":
        advice["next_steps"].append("UK: confirm UKVI latest rules + funds proof; apply early for Sep intake.")
    elif (country.get("code") or "").upper() == "US":
        advice["next_steps"].append("US: check GRE/GMAT requirement; plan 8–12 months earlier for timeline.")

    return advice


# =====================================================
#  ROUTES
# =====================================================

@app.route("/")
def root():
    return jsonify({
        "message": "Beast Consultancy Backend is running.",
        "available_endpoints": [
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
    country = COUNTRY_BY_CODE.get((country_code or "").upper())
    if not country:
        return jsonify({"error": "Country not found"}), 404

    clusters = {}
    for uni in country.get("universities", []):
        for course in (uni.get("courses") or []):
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

    cgpa = safe_float(data.get("cgpa", 0), 0.0)
    budget_lakhs = safe_float(data.get("budget_lakhs", 0), 0.0)
    backlogs = safe_int(data.get("backlogs_count", 0), 0)
    work_ex_years = safe_float(data.get("work_ex_years", 0), 0.0)
    english_score = safe_float(data.get("english_score", 0), 0.0)

    subject_clusters = data.get("subject_clusters") or []
    subject_clusters = [c for c in subject_clusters if c]

    target_intake = data.get("target_intake", "")
    intake_month = month_from_intake_string(target_intake)

    profile = {
        "name": data.get("name") or "Student",
        "country_code": country_code,
        "cgpa": cgpa,
        "backlogs_count": backlogs,
        "english_proof_type": (data.get("english_proof_type") or "").lower(),
        "english_score": english_score,
        "budget_lakhs": budget_lakhs,
        "work_ex_years": work_ex_years,
        "non_math_background": bool(data.get("non_math_background", False)),
        "target_intake": target_intake,
        "intake_month": intake_month,
    }

    # =================================================
    #   HARD FILTER: country + subject + backlog (strict) + CGPA strict band (reject removed)
    # =================================================
    matches = []
    for merged in DB["flat_courses"]:
        if merged["country_code"] != country_code:
            continue

        course = merged["course"]

        # subject filter
        cluster = course.get("subject_cluster", "")
        if subject_clusters and cluster not in subject_clusters:
            continue

        # backlogs strict filter (max_backlogs handled later too, but we prune early)
        max_backlogs = course.get("max_backlogs")
        if max_backlogs is not None and backlogs > safe_int(max_backlogs, 0):
            continue
        if not course.get("accepts_backlog_history", True) and backlogs > 0:
            continue

        # CGPA strict reject early
        min_cgpa = safe_float(course.get("min_cgpa_india", 0) or 0, 0)
        band = classify_level(cgpa, min_cgpa)
        if band == "reject":
            continue

        matches.append(merged)

    # =================================================
    #   TRANSFORM TO RESPONSE OBJECTS (with fit + prob)
    # =================================================
    course_items = []
    for merged in matches:
        item = build_course_response(merged, profile)
        if item:
            course_items.append(item)

    # Sort primarily by fit_score desc, then probability desc, then cost asc
    course_items.sort(
        key=lambda c: (-c.get("fit_score", 0), -c.get("admission_probability", 0), c.get("total_first_year_cost_lakhs", 0))
    )

    requested_count = safe_int(data.get("requested_count", 7), 7)
    requested_count = max(1, min(requested_count, 15))
    course_items = course_items[:requested_count]

    advice = global_advice_from_results(country, profile, course_items)

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
            "total_shown": len(course_items),
            "safe_count": sum(1 for c in course_items if c.get("level_band") == "safe"),
            "moderate_count": sum(1 for c in course_items if c.get("level_band") == "moderate"),
            "ambitious_count": sum(1 for c in course_items if c.get("level_band") == "ambitious"),
        },
        "recommendations": course_items,
        "global_advice": advice,
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)