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
            # Just skip if the file doesn't exist yet
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
            # If format is unexpected, we just ignore that file for now
            print(f"[WARN] {filename} has unexpected format, skipped.")

    if not countries:
        raise ValueError("No valid countries loaded from JSON files.")

    flat_courses = []

    for country in countries:
        c_code = country.get("code")
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
COUNTRY_BY_CODE = {c.get("code"): c for c in DB["countries"]}

   
    


DB = load_db()
COUNTRY_BY_CODE = {c.get("code"): c for c in DB["countries"]}


# =====================================================
#  HELPER FUNCTIONS
# =====================================================

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


def build_tier_label(tier_band: str):
    mapping = {
        "russell_group_top": "Russell Group / Top UK research university",
        "public_research": "Public research university",
        "teaching_focused": "Teaching-focused / modern university",
        "general_public": "General public university",
        "private": "Private / specialist institution",
    }
    return mapping.get(tier_band, "General university")


def english_ok_for_course(course, profile):
    """
    Check if student's English proof matches course requirement.
    Also returns english_gap flag for advice.
    """
    proof = profile["english_proof_type"]
    score = profile["english_score"]

    min_ielts = course.get("min_ielts_overall")
    min_pte = course.get("min_pte_overall")
    min_duo = course.get("min_duolingo")
    inter_ok = course.get("inter_english_ok", False)

    # No test provided
    if proof in ("none", None, ""):
        return False, True  # not ok, big gap

    if proof == "ielts":
        if min_ielts is None:
            return True, False
        return score >= min_ielts, score < min_ielts

    if proof == "pte":
        if min_pte is None:
            return True, False
        return score >= min_pte, score < min_pte

    if proof == "duolingo":
        if min_duo is None:
            return True, False
        return score >= min_duo, score < min_duo

    if proof in ("inter", "medium"):
        # depends on course + country flags
        if inter_ok and COUNTRY_BY_CODE.get(profile["country_code"], {}).get(
            "allow_inter_english", False
        ):
            return True, False
        else:
            return False, True

    # unknown type => treat as gap
    return False, True


def build_why_country(country):
    reasons = []

    # main reasons
    for r in country.get("reasons_to_choose", [])[:3]:
        reasons.append(r)

    notes = country.get("admission_notes")
    if notes:
        reasons.append(notes)

    # visa info
    visa_rules = country.get("visa_rules") or {}
    work_hrs = visa_rules.get("work_during_studies_hours_per_week")
    if work_hrs:
        reasons.append(
            f"Can usually work up to {work_hrs} hours/week during studies (check latest official rules)."
        )
    psw = visa_rules.get("post_study_work_options")
    if psw:
        reasons.append(f"Post-study work route: {psw}")

    return reasons


def build_why_university(uni):
    reasons = []
    for h in uni.get("highlights", [])[:3]:
        reasons.append(h)

    city_notes = uni.get("city_notes")
    if city_notes:
        reasons.append(city_notes)

    ranking = uni.get("ranking_band_global")
    if ranking:
        reasons.append(f"Approx global ranking band: {ranking}.")

    return reasons


def build_why_course(course):
    reasons = []
    for h in course.get("course_highlights", [])[:3]:
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
    pros.extend(uni.get("highlights", []))
    pros.extend(course.get("course_highlights", []))
    return pros[:8]  # cap to avoid huge list


def build_cons(merged):
    uni = merged["university"]
    course = merged["course"]
    cons = []
    cons.extend(uni.get("cautions", []))
    cons.extend(course.get("course_cautions", []))

    if not cons:
        cons.append(
            "No major public red flags, but always cross-check recent reviews, outcomes and visa updates."
        )
    return cons[:8]


def compute_risk_flags(merged, profile, level_band, english_gap, budget_label):
    course = merged["course"]
    uni = merged["university"]

    risks = {
        "budget_risk": budget_label == "over_budget",
        "english_gap": english_gap,
        "cgpa_gap": level_band == "ambitious",
        "math_risk": False,
        "workex_gap": False,
        "visa_risk_high": uni.get("visa_risk") == "high",
    }

    if course.get("math_required") and profile.get("non_math_background"):
        risks["math_risk"] = True

    if course.get("work_exp_required_years", 0) > profile.get("work_ex_years", 0):
        risks["workex_gap"] = True

    return risks


def build_course_response(merged, profile):
    """
    Convert merged course+uni+country into a clean JSON card
    with why_country / why_university / why_course / pros / cons / risk / advice.
    """
    country = merged["country"]
    uni = merged["university"]
    course = merged["course"]

    # --- academic strictness ---
    cgpa = profile["cgpa"]
    min_cgpa = course.get("min_cgpa_india", 0) or 0
    level_band = classify_level(cgpa, min_cgpa)

    # very weak academic match -> drop
    if level_band == "reject":
        return None

    # --- budget ---
    tuition = float(course.get("tuition_fee_lakhs", 0) or 0)
    living = float(course.get("estimated_living_lakhs", 0) or 0)
    extra = float(course.get("extra_costs_lakhs", 0) or 0)
    total = tuition + living + extra

    budget = float(profile["budget_lakhs"])
    budget_label = budget_fit_label(total, budget)

    # --- English ---
    english_ok, english_gap = english_ok_for_course(course, profile)

    # --- risks ---
    risks = compute_risk_flags(merged, profile, level_band, english_gap, budget_label)

    # --- labels / text ---
    tier_label = build_tier_label(uni.get("tier_band"))
    intakes = course.get("intakes", [])
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

    budget_text_map = {
        "very_comfortable": "Your budget is very comfortable for this option.",
        "tight_but_possible": "Your budget is just enough; you must manage money carefully.",
        "over_budget": "This is above your current stated budget. Consider scholarships or higher funds.",
        "unknown": "Budget evaluation not available.",
    }

    advice_parts = []

    if level_band == "safe":
        advice_parts.append("Academically this is a SAFE match for your CGPA.")
    elif level_band == "moderate":
        advice_parts.append("Academically this is a MODERATE (balanced) match for your CGPA.")
    elif level_band == "ambitious":
        advice_parts.append("This is an AMBITIOUS option for your CGPA. You must show strong projects/SOP.")

    advice_parts.append(budget_text_map[budget_label])

    if english_gap:
        advice_parts.append(
            "You must improve or prove English (IELTS/PTE/Duolingo) to match this course requirement."
        )
    if risks["math_risk"]:
        advice_parts.append(
            "Strong maths is required – revise core maths & statistics before going for this program."
        )
    if risks["workex_gap"]:
        advice_parts.append(
            "More relevant full-time work experience would make your profile stronger for this course."
        )

    short_advice = " ".join(advice_parts)

    return {
        "course_id": course.get("id"),
        "country_code": country.get("code"),
        "country_name": country.get("name"),
        "university_name": uni.get("name", "Unknown University"),
        "city": uni.get("city", ""),
        "course_name": course.get("name"),
        "subject_cluster": course.get("subject_cluster"),
        "level_band": level_band,      # safe / moderate / ambitious
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
        "why_country": why_country,
        "why_university": why_uni,
        "why_course": why_course,
        "pros": pros,
        "cons": cons,
        "risk_flags": risks,
        "short_advice": short_advice,
        "official_course_url": course.get("official_course_url"),
    }


def global_advice_from_results(country, profile, course_items):
    """
    Build overall advice: why that country, what to improve, next steps.
    """
    advice = {
        "headline": "",
        "english_advice": "",
        "budget_advice": "",
        "profile_gaps": [],
        "next_steps": [],
    }

    if not course_items:
        advice["headline"] = "No strong matches found in this country with current filters."
        advice["next_steps"].append(
            "Try improving IELTS/PTE score, increasing budget, or exploring more teaching-focused universities."
        )
        advice["next_steps"].append(
            "You can also try a different country or slightly different course combination (e.g., general CS instead of AI-only)."
        )
        return advice

    safe_count = sum(1 for c in course_items if c["level_band"] == "safe")
    mod_count = sum(1 for c in course_items if c["level_band"] == "moderate")
    amb_count = sum(1 for c in course_items if c["level_band"] == "ambitious")

    if safe_count >= 3:
        advice["headline"] = (
            "You have several SAFE options – shortlist 2–3 safe and keep 1–2 ambitious as backup."
        )
    elif mod_count > 0 or amb_count > 0:
        advice["headline"] = (
            "Most options are MODERATE or AMBITIOUS – you need strong projects, SOP and LORs."
        )

    # English advice
    needs_test = profile["english_proof_type"] in ("none", "inter", "medium")
    if needs_test:
        advice["english_advice"] = (
            "Taking IELTS / PTE / Duolingo will open many more universities and make visa stronger, "
            "even if some accept Inter/Medium English."
        )
    else:
        advice["english_advice"] = (
            "Your chosen English test looks okay; just ensure you meet each course's minimum sub-scores."
        )

    # Budget advice
    over_budget_count = sum(1 for c in course_items if c["budget_label"] == "over_budget")
    if over_budget_count > 0:
        advice["budget_advice"] = (
            "Some options are above your current budget. Plan for extra funds, education loans or scholarships, "
            "or target lower-cost cities/universities."
        )
    else:
        advice["budget_advice"] = "Your budget seems reasonable for the recommended universities."

    # Profile gaps
    if any(c["risk_flags"]["math_risk"] for c in course_items):
        advice["profile_gaps"].append(
            "Strengthen your maths and statistics basics – especially for Data Science / AI / Analytics programs."
        )
    if any(c["risk_flags"]["workex_gap"] for c in course_items):
        advice["profile_gaps"].append(
            "More relevant full-time work experience will make your MBA / Project Management profile much stronger."
        )

    # Country-specific notes
    country_name = country.get("name")
    if country_name == "United Kingdom":
        advice["next_steps"].append(
            "For the UK, track university application deadlines and CAS dates and always confirm latest UKVI visa rules."
        )
    elif country_name == "United States":
        advice["next_steps"].append(
            "For the US, check if GRE/GMAT is recommended for your course and plan applications 8–12 months before intake."
        )

    advice["next_steps"].append(
        "Prepare a strong SOP, updated CV, transcripts, and at least 1–2 solid LORs before you start applying."
    )

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
    """
    Return minimal list of countries for dropdown.
    """
    items = []
    for c in DB["countries"]:
        items.append({
            "code": c.get("code"),
            "name": c.get("name"),
            "flag": c.get("flag", ""),
            "default_currency": c.get("default_currency"),
        })
    return jsonify(items)


@app.route("/courses/<country_code>", methods=["GET"])
def get_courses(country_code):
    """
    For a country, return available subject_clusters (Data Science, AI, MBA, etc.)
    with example course + count.
    """
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
    """
    Main recommendation endpoint.
    Frontend should POST JSON like:
      {
        "name": "Sidhu",
        "country_code": "UK",
        "cgpa": 8.2,
        "backlogs_count": 0,
        "english_proof_type": "ielts" | "pte" | "duolingo" | "inter" | "medium" | "none",
        "english_score": 6.5,
        "budget_lakhs": 30,
        "work_ex_years": 0,
        "non_math_background": false,
        "subject_clusters": ["data_science", "artificial_intelligence"],
        "target_intake": "Sep 2026",
        "requested_count": 8
      }
    """
    data = request.get_json(force=True) or {}

    # ---- basic fields ----
    country_code = (data.get("country_code") or "UK").upper()
    country = COUNTRY_BY_CODE.get(country_code)
    if not country:
        return jsonify({"error": "Invalid or unsupported country_code"}), 400

    try:
        cgpa = float(data.get("cgpa", 0))
    except ValueError:
        cgpa = 0.0

    try:
        budget_lakhs = float(data.get("budget_lakhs", 0))
    except ValueError:
        budget_lakhs = 0.0

    try:
        backlogs = int(data.get("backlogs_count", 0))
    except ValueError:
        backlogs = 0

    try:
        work_ex_years = float(data.get("work_ex_years", 0))
    except ValueError:
        work_ex_years = 0.0

    english_score_raw = data.get("english_score", 0)
    try:
        english_score = float(english_score_raw)
    except ValueError:
        english_score = 0.0

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
        "non_math_background": data.get("non_math_background", False),
        "target_intake": target_intake,
        "intake_month": intake_month,
    }

    # =================================================
    #   HARD FILTER: country + subject + backlogs + CGPA
    # =================================================
    matches = []

    for merged in DB["flat_courses"]:
        if merged["country_code"] != country_code:
            continue

        course = merged["course"]

        # subject filter (if user selected)
        cluster = course.get("subject_cluster", "")
        if subject_clusters and cluster not in subject_clusters:
            continue

        # backlogs filter
        max_backlogs = course.get("max_backlogs")
        if max_backlogs is not None and backlogs > max_backlogs:
            continue
        if not course.get("accepts_backlog_history", True) and backlogs > 0:
            continue

        # intake awareness (we don't strictly reject, we just note)
        intakes = course.get("intakes") or []
        if intakes and intake_month:
            # if intake_month not in intakes:
            #     we still keep it, but frontend can show 'not exact intake'
            pass

        # CGPA strictness
        min_cgpa = course.get("min_cgpa_india", 0) or 0
        level_band = classify_level(cgpa, min_cgpa)
        if level_band == "reject":
            continue

        matches.append(merged)

    # =================================================
    #   TRANSFORM TO RESPONSE OBJECTS
    # =================================================
    course_items = []
    for merged in matches:
        item = build_course_response(merged, profile)
        if item:
            course_items.append(item)

    # Ensure we always have at least 1 ambitious if possible
    # (so student sees a dream option)
    ambitious_items = [c for c in course_items if c["level_band"] == "ambitious"]

    # Sort: safe > moderate > ambitious, then by total cost
    level_order = {"safe": 0, "moderate": 1, "ambitious": 2, "unknown": 3}
    course_items.sort(
        key=lambda c: (
            level_order.get(c["level_band"], 3),
            c["total_first_year_cost_lakhs"],
        )
    )

    requested_count = int(data.get("requested_count", 5) or 5)
    requested_count = max(1, min(requested_count, 15))

    course_items = course_items[:requested_count]

    # If no ambitious inside top N but ambitious existed in pool, add one extra
    if not any(c["level_band"] == "ambitious" for c in course_items) and ambitious_items:
        course_items.append(ambitious_items[0])

    # =================================================
    #   GLOBAL ADVICE
    # =================================================
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
            "safe_count": sum(1 for c in course_items if c["level_band"] == "safe"),
            "moderate_count": sum(1 for c in course_items if c["level_band"] == "moderate"),
            "ambitious_count": sum(1 for c in course_items if c["level_band"] == "ambitious"),
        },
        "recommendations": course_items,
        "global_advice": advice,
    }

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
