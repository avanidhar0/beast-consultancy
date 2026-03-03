// beast-frontend/src/App.jsx
import React, { useEffect, useMemo, useState } from "react";

const API_BASE = "https://beast-consultancy.onrender.com";

// ----------------- Small helpers -----------------
const COUNTRY_CONFIG = {
  UK: {
    name: "United Kingdom",
    flag: "🇬🇧",
    tagline: "1-year Masters, 2-year PSW, strong for Data & Management.",
    bullets: [
      "1-year Masters, 2-year PSW.",
      "Strong for Data Science, CS, MBA.",
      "Budget-friendly options outside London.",
    ],
    chips: ["Data / CS strong", "MBA / Business", "Lower fees vs US"],
    extra_notes: [
      "UKVI still often prefers IELTS/PTE even if some universities accept Inter/Medium.",
      "Apply early for Sep intake (best) – seats fill fast.",
    ],
  },
  US: {
    name: "United States",
    flag: "🇺🇸",
    tagline: "STEM + OPT up to 3 years, strong for CS & AI.",
    bullets: [
      "2-year Masters, strong research culture.",
      "STEM → up to 3 years OPT (work).",
      "Very strong for CS, AI, Data.",
    ],
    chips: ["Top for CS / AI", "High budget", "Needs IELTS/TOEFL"],
    extra_notes: [
      "Many universities may ask GRE/GMAT (Required/Recommended varies by program).",
      "Plan 8–12 months early for US admissions timelines.",
    ],
  },
};

const DEFAULT_PROFILE = {
  name: "",
  cgpa: "",
  backlogs: "0",
  workEx: "0",
  englishProof: "inter",
  englishScore: "70",
  nonMath: false,
  intake: "Sep 2026",
  budget: "30",
  maxUnis: "7",
  clusters: [],
};

const CLUSTER_ICONS = {
  data_science: "📊",
  computer_science: "💻",
  artificial_intelligence: "🤖",
  mba: "💼",
  business_analytics: "📈",
  cyber_security: "🛡️",
  information_systems: "🗄️",
  project_management: "📋",
  it: "🖥️",
  other: "📚",
};

// ----------------- Validation helpers -----------------
const toNum = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : NaN;
};

function validateProfileStep1(p) {
  const errors = {};

  const name = (p.name || "").trim();
  if (!name) errors.name = "Name is required.";

  const cgpa = toNum(p.cgpa);
  if (!Number.isFinite(cgpa)) errors.cgpa = "Enter CGPA number (e.g. 8.2).";
  else if (cgpa <= 0 || cgpa > 10) errors.cgpa = "CGPA must be between 0 and 10.";

  const backlogs = toNum(p.backlogs);
  if (!Number.isFinite(backlogs) || backlogs < 0) errors.backlogs = "Backlogs must be 0 or more.";

  const workEx = toNum(p.workEx);
  if (!Number.isFinite(workEx) || workEx < 0) errors.workEx = "Work-ex must be 0 or more.";

  const proof = (p.englishProof || "").toLowerCase();
  if (!proof) errors.englishProof = "Select English proof type.";

  const score = toNum(p.englishScore);
  if (!Number.isFinite(score)) errors.englishScore = "Enter a valid score/percentage.";
  else {
    if (proof === "ielts" && (score < 0 || score > 9)) errors.englishScore = "IELTS must be 0–9.";
    if (proof === "pte" && (score < 10 || score > 90)) errors.englishScore = "PTE must be 10–90.";
    if (proof === "duolingo" && (score < 10 || score > 160)) errors.englishScore = "Duolingo must be 10–160.";
    if ((proof === "inter" || proof === "medium") && (score < 0 || score > 100))
      errors.englishScore = "Inter/Medium % must be 0–100.";
  }

  return errors;
}

function validateProfileStep2(p) {
  const errors = {};

  const intake = (p.intake || "").trim();
  if (!intake) errors.intake = "Intake is required (e.g. Sep 2026).";

  const budget = toNum(p.budget);
  if (!Number.isFinite(budget)) errors.budget = "Budget must be a number (lakhs).";
  else if (budget <= 0) errors.budget = "Budget must be > 0.";

  const maxUnis = toNum(p.maxUnis);
  if (!Number.isFinite(maxUnis)) errors.maxUnis = "Enter a number (1–15).";
  else if (maxUnis < 1 || maxUnis > 15) errors.maxUnis = "Max universities must be 1–15.";

  if (!Array.isArray(p.clusters) || p.clusters.length === 0) {
    errors.clusters = "Please select at least 1 course cluster.";
  }

  return errors;
}

// ----------------- Main App -----------------
function App() {
  const [view, setView] = useState("landing"); // landing | form | results
  const [selectedCountry, setSelectedCountry] = useState("UK");
  const [formStep, setFormStep] = useState(1); // 1 or 2
  const [profile, setProfile] = useState(DEFAULT_PROFILE);

  const [errors1, setErrors1] = useState({});
  const [errors2, setErrors2] = useState({});

  const [clustersByCountry, setClustersByCountry] = useState({});
  const [loadingClusters, setLoadingClusters] = useState(false);
  const [clusterError, setClusterError] = useState("");

  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsError, setRecsError] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [selectedRecId, setSelectedRecId] = useState(null);
  const [globalAdvice, setGlobalAdvice] = useState(null);

  const [compareIds, setCompareIds] = useState([]);
  const [isBotOpen, setIsBotOpen] = useState(false);

  // ------- Load course clusters when country changes -------
  useEffect(() => {
    async function fetchClusters() {
      setLoadingClusters(true);
      setClusterError("");
      try {
        const res = await fetch(`${API_BASE}/courses/${selectedCountry}`);
        if (!res.ok) throw new Error("Failed to load course clusters");
        const data = await res.json();
        setClustersByCountry((prev) => ({
          ...prev,
          [selectedCountry]: data,
        }));
      } catch (err) {
        console.error(err);
        setClusterError("Could not load course options. Try again.");
      } finally {
        setLoadingClusters(false);
      }
    }

    if (!clustersByCountry[selectedCountry]) fetchClusters();
  }, [selectedCountry, clustersByCountry]);

  const currentClusters = clustersByCountry[selectedCountry] || [];

  const selectedRec = useMemo(() => {
    return (
      recommendations.find((r) => r.course_id === selectedRecId) ||
      recommendations[0] ||
      null
    );
  }, [recommendations, selectedRecId]);

  const safeCount = recommendations.filter((r) => r.level_band === "safe").length;
  const moderateCount = recommendations.filter((r) => r.level_band === "moderate").length;
  const ambitiousCount = recommendations.filter((r) => r.level_band === "ambitious").length;

  const handleStart = () => {
    setView("form");
    setFormStep(1);
    setErrors1({});
    setErrors2({});
  };

  const updateProfileField = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  };

  const toggleCluster = (cluster) => {
    setProfile((prev) => {
      const exists = prev.clusters.includes(cluster);
      return {
        ...prev,
        clusters: exists ? prev.clusters.filter((c) => c !== cluster) : [...prev.clusters, cluster],
      };
    });
  };

  const goToStep2 = () => {
    const e = validateProfileStep1(profile);
    setErrors1(e);
    if (Object.keys(e).length === 0) setFormStep(2);
  };

  const handleFindUniversities = async () => {
    const e1 = validateProfileStep1(profile);
    const e2 = validateProfileStep2(profile);
    setErrors1(e1);
    setErrors2(e2);
    if (Object.keys(e1).length || Object.keys(e2).length) return;

    try {
      setLoadingRecs(true);
      setRecsError("");
      setRecommendations([]);
      setSelectedRecId(null);
      setGlobalAdvice(null);
      setCompareIds([]);

      const payload = {
        name: profile.name || "Student",
        country_code: selectedCountry,
        cgpa: Number(profile.cgpa || 0),
        backlogs_count: Number(profile.backlogs || 0),
        english_proof_type: profile.englishProof,
        english_score: Number(profile.englishScore || 0),
        budget_lakhs: Number(profile.budget || 0),
        work_ex_years: Number(profile.workEx || 0),
        non_math_background: profile.nonMath,
        subject_clusters: profile.clusters,
        target_intake: profile.intake,
        requested_count: Number(profile.maxUnis || 7),
      };

      const res = await fetch(`${API_BASE}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Recommendation API failed");
      const data = await res.json();

      setRecommendations(data.recommendations || []);
      setGlobalAdvice(data.global_advice || null);

      if ((data.recommendations || []).length > 0) {
        setSelectedRecId(data.recommendations[0].course_id);
      }
      setView("results");
    } catch (err) {
      console.error(err);
      setRecsError("Failed to load recommendations. Check backend or try again.");
      setView("results");
    } finally {
      setLoadingRecs(false);
    }
  };

  const toggleCompare = (courseId) => {
    setCompareIds((prev) => {
      if (prev.includes(courseId)) return prev.filter((id) => id !== courseId);
      if (prev.length >= 4) return prev;
      return [...prev, courseId];
    });
  };

  const resetToLanding = () => {
    setView("landing");
    setFormStep(1);
    setProfile(DEFAULT_PROFILE);
    setErrors1({});
    setErrors2({});
    setRecommendations([]);
    setSelectedRecId(null);
    setGlobalAdvice(null);
    setCompareIds([]);
    setIsBotOpen(false);
  };

  // ----------------- UI Pieces -----------------
  const renderHeader = (rightNode) => (
    <header className="app-header header-upgraded">
      <div className="brand-left">
        <div className="logo-circle">🎓</div>

        <div className="brand-text">
          <div className="brand-title">Beast Consultancy</div>
          <div className="brand-sub">
            Strict, realistic admissions engine – powered by your own DB.
          </div>
          <div className="built-by-inline">Product design &amp; build by Avanidhar 🚀</div>
        </div>
      </div>

      {rightNode || <div className="header-right-pill">Offline rules • No API keys</div>}
    </header>
  );

  const renderLanding = () => {
    const cInfo = COUNTRY_CONFIG[selectedCountry];

    return (
      <div className="landing">
        {renderHeader(<div className="header-right-pill">Offline rules • No API keys</div>)}

        <main className="landing-main">
          <section className="hero-text">
            <h1>Choose your study destination 🌍</h1>
            <p>
              Start with <strong>UK</strong> or <strong>US</strong> now – later we can add Canada, Australia,
              Germany with the same Beast engine.
            </p>

            <div className="hero-cta-row">
              <button className="btn primary" onClick={handleStart}>
                Continue with {cInfo.flag} {cInfo.name}
              </button>
              <div className="hero-cta-hint">Select country card below if you want to switch.</div>
            </div>
          </section>

          <section className="country-grid">
            {["UK", "US"].map((code) => {
              const c = COUNTRY_CONFIG[code];
              const selected = selectedCountry === code;
              return (
                <button
                  key={code}
                  className={`country-card ${selected ? "selected" : ""}`}
                  onClick={() => setSelectedCountry(code)}
                >
                  <div className="country-flag">{c.flag}</div>
                  <div className="country-name">
                    {c.name} {selected && <span className="country-selected-dot">●</span>}
                  </div>
                  <div className="country-tagline">{c.tagline}</div>
                  <ul className="country-bullets">
                    {c.bullets.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                  <div className="country-chips">
                    {c.chips.map((chip) => (
                      <span key={chip} className="chip">
                        {chip}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })}

            {[
              { code: "CA", name: "Canada", flag: "🇨🇦" },
              { code: "AU", name: "Australia", flag: "🇦🇺" },
            ].map((c) => (
              <div key={c.code} className="country-card coming-soon">
                <div className="country-flag">{c.flag}</div>
                <div className="country-name">{c.name}</div>
                <div className="coming-label">Coming soon</div>
              </div>
            ))}
          </section>
        </main>
      </div>
    );
  };

  const renderProfileForm = () => {
    const cInfo = COUNTRY_CONFIG[selectedCountry];

    return (
      <div className="app-shell">
        {renderHeader(
          <div className="header-country-pill">
            {cInfo.flag} {cInfo.name}
          </div>
        )}

        <main className="main-layout">
          <section className="left-panel">
            <div className="breadcrumb">
              <span className={formStep === 1 ? "active" : ""}>1 · Profile</span>
              <span>→</span>
              <span className={formStep === 2 ? "active" : ""}>2 · Preferences</span>
              <span>→</span>
              <span>3 · Recommendations</span>
            </div>

            <div className="form-card">
              <div className="form-card-header">
                <h2>Student profile 🧑‍🎓</h2>
                <p>
                  Fields with <span className="req-star">*</span> are mandatory.
                </p>
              </div>

              {formStep === 1 && (
                <div className="form-grid">
                  <div className="form-field">
                    <label>
                      Name <span className="req-star">*</span>
                    </label>
                    <input
                      value={profile.name}
                      onChange={(e) => updateProfileField("name", e.target.value)}
                      placeholder="Your name"
                    />
                    {errors1.name && <div className="field-note error">{errors1.name}</div>}
                  </div>

                  <div className="form-field">
                    <label>
                      CGPA (out of 10) <span className="req-star">*</span>
                    </label>
                    <input
                      value={profile.cgpa}
                      onChange={(e) => updateProfileField("cgpa", e.target.value)}
                      placeholder="e.g. 8.2"
                      inputMode="decimal"
                    />
                    {errors1.cgpa && <div className="field-note error">{errors1.cgpa}</div>}
                  </div>

                  <div className="form-field">
                    <label>
                      Backlogs (completed) <span className="req-star">*</span>
                    </label>
                    <input
                      value={profile.backlogs}
                      onChange={(e) => updateProfileField("backlogs", e.target.value)}
                      placeholder="0"
                      inputMode="numeric"
                    />
                    {errors1.backlogs && <div className="field-note error">{errors1.backlogs}</div>}
                  </div>

                  <div className="form-field">
                    <label>
                      Work-experience (years) <span className="req-star">*</span>
                    </label>
                    <input
                      value={profile.workEx}
                      onChange={(e) => updateProfileField("workEx", e.target.value)}
                      placeholder="0"
                      inputMode="decimal"
                    />
                    {errors1.workEx && <div className="field-note error">{errors1.workEx}</div>}
                  </div>

                  <div className="form-field">
                    <label>
                      English proof <span className="req-star">*</span>
                    </label>
                    <select
                      value={profile.englishProof}
                      onChange={(e) => updateProfileField("englishProof", e.target.value)}
                    >
                      <option value="ielts">IELTS</option>
                      <option value="pte">PTE</option>
                      <option value="duolingo">Duolingo</option>
                      <option value="inter">Inter English</option>
                      <option value="medium">Medium of Instruction</option>
                      <option value="none">No test yet</option>
                    </select>
                    {errors1.englishProof && <div className="field-note error">{errors1.englishProof}</div>}
                  </div>

                  <div className="form-field">
                    <label>
                      Score / % <span className="req-star">*</span>
                    </label>
                    <input
                      value={profile.englishScore}
                      onChange={(e) => updateProfileField("englishScore", e.target.value)}
                      placeholder="e.g. 6.5 or 70"
                      inputMode="decimal"
                    />
                    {errors1.englishScore && <div className="field-note error">{errors1.englishScore}</div>}
                  </div>

                  <div className="form-field full">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={profile.nonMath}
                        onChange={(e) => updateProfileField("nonMath", e.target.checked)}
                      />
                      <span>I am from a non-math / non-CS background</span>
                    </label>
                  </div>

                  <div className="form-actions full">
                    <button className="btn ghost" onClick={resetToLanding}>
                      ← Back to countries
                    </button>
                    <button className="btn primary" onClick={goToStep2}>
                      Next → Preferences
                    </button>
                  </div>
                </div>
              )}

              {formStep === 2 && (
                <div className="pref-layout">
                  <div className="pref-left">
                    <div className="form-field full">
                      <label>Selected country</label>
                      <div className="country-pill-large">
                        {cInfo.flag} {cInfo.name}
                      </div>
                    </div>

                    <div className="form-field">
                      <label>
                        Preferred intake <span className="req-star">*</span>
                      </label>
                      <input
                        value={profile.intake}
                        onChange={(e) => updateProfileField("intake", e.target.value)}
                        placeholder="e.g. Sep 2026"
                      />
                      {errors2.intake && <div className="field-note error">{errors2.intake}</div>}
                    </div>

                    <div className="form-field">
                      <label>
                        Budget for first year (lakhs) <span className="req-star">*</span>
                      </label>
                      <input
                        value={profile.budget}
                        onChange={(e) => updateProfileField("budget", e.target.value)}
                        placeholder="e.g. 30"
                        inputMode="decimal"
                      />
                      {errors2.budget && <div className="field-note error">{errors2.budget}</div>}
                    </div>

                    <div className="form-field">
                      <label>
                        How many universities to show? <span className="req-star">*</span>
                      </label>
                      <input
                        value={profile.maxUnis}
                        onChange={(e) => updateProfileField("maxUnis", e.target.value)}
                        placeholder="e.g. 7"
                        inputMode="numeric"
                      />
                      {errors2.maxUnis && <div className="field-note error">{errors2.maxUnis}</div>}
                      <div className="field-note">Max 15 – engine will include at least 1 ambitious if possible.</div>
                    </div>

                    <div className="form-actions full">
                      <button className="btn ghost" onClick={() => setFormStep(1)}>
                        ← Back to profile
                      </button>
                      <button className="btn primary" onClick={handleFindUniversities} disabled={loadingRecs}>
                        {loadingRecs ? "Finding universities…" : "Find universities"}
                      </button>
                    </div>
                  </div>

                  <div className="pref-right">
                    <div className="form-field full">
                      <label>Choose course clusters</label>
                      {loadingClusters && <div className="field-note">Loading options…</div>}
                      {clusterError && <div className="field-note error">{clusterError}</div>}
                      {errors2.clusters && <div className="field-note error">{errors2.clusters}</div>}

                      <div className="cluster-panel">
                        <div className="cluster-grid">
                          {currentClusters.map((cl) => {
                            const active = profile.clusters.includes(cl.subject_cluster);
                            const icon = CLUSTER_ICONS[cl.subject_cluster] || "📚";

                            return (
                              <button
                                type="button"
                                key={cl.subject_cluster}
                                className={`cluster-tile ${active ? "active" : ""}`}
                                onClick={() => toggleCluster(cl.subject_cluster)}
                              >
                                <div className="cluster-icon">{icon}</div>
                                <div className="cluster-title">{cl.display_name}</div>
                                <div className="cluster-sub">{cl.example_course}</div>
                                <div className="cluster-count">{cl.count} course(s)</div>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="field-note">Tip: Pick 2–3 clusters for best matching.</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="right-panel">
            <div className="country-info-card">
              <h3>About {cInfo.name}</h3>
              <p>{cInfo.tagline}</p>
              <ul>
                {cInfo.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <div className="country-extra">
                {cInfo.extra_notes.map((n) => (
                  <div key={n} className="note-pill">💡 {n}</div>
                ))}
              </div>
            </div>
          </section>
        </main>
      </div>
    );
  };

  const renderResults = () => {
    const cInfo = COUNTRY_CONFIG[selectedCountry];
    const compareRecs = recommendations.filter((r) => compareIds.includes(r.course_id));

    return (
      <div className="app-shell">
        {renderHeader(
          <div className="header-country-pill">
            {cInfo.flag} {cInfo.name}
          </div>
        )}

        <main className="main-layout">
          <section className="left-panel results-list">
            <div className="summary-card">
              <h2>Recommendations 🎯</h2>
              <p>
                Profile for <strong>{profile.name || "Student"}</strong> · CGPA{" "}
                <strong>{profile.cgpa || "?"}</strong> · Budget <strong>{profile.budget || "?"}L</strong>
              </p>

              <div className="summary-pills">
                <span className="pill safe">Safe: {safeCount}</span>
                <span className="pill moderate">Moderate: {moderateCount}</span>
                <span className="pill ambitious">Ambitious: {ambitiousCount}</span>
              </div>

              <button className="btn ghost small" onClick={() => setView("form")}>
                ← Back to form
              </button>
              <button className="btn ghost small" onClick={resetToLanding}>
                ← Back to countries
              </button>
            </div>

            {recsError && <div className="error-box small">{recsError}</div>}
            {recommendations.length === 0 && !loadingRecs && (
              <div className="no-results-box">
                No recommendations yet. Try adjusting CGPA, budget or English and click <b>Find universities</b>.
              </div>
            )}
            {loadingRecs && <div className="loading-box">Finding realistic options…</div>}

            <div className="uni-list">
              {recommendations.map((rec) => {
                const active = rec.course_id === selectedRecId;
                return (
                  <div
                    key={rec.course_id}
                    className={`uni-row ${active ? "active" : ""}`}
                    onClick={() => setSelectedRecId(rec.course_id)}
                  >
                    <div className="uni-row-main">
                      <div>
                        <div className="uni-row-name">
                          {rec.university_name} – {rec.city}
                        </div>
                        <div className="uni-row-course">{rec.course_name}</div>

                        <div className="uni-row-meta">
                          <span className={`pill level-${rec.level_band}`}>{rec.level_band.toUpperCase()}</span>
                          <span className="pill subtle">Fit: {rec.fit_score ?? "?"}/100</span>
                          <span className="pill subtle">Admit: {rec.admission_probability ?? "?"}%</span>
                          <span className="pill subtle">Visa: {rec.visa_risk || "?"}</span>
                          <span className="pill subtle">1st year: {rec.total_first_year_cost_lakhs}L</span>
                          <span className="pill subtle">Intakes: {rec.intakes_text}</span>
                        </div>
                      </div>
                    </div>

                    <div className="uni-row-actions">
                      <label className="checkbox-label small" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={compareIds.includes(rec.course_id)}
                          onChange={() => toggleCompare(rec.course_id)}
                        />
                        <span>Compare</span>
                      </label>
                      <div className="uni-row-hint">Click for details →</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="right-panel results-detail">
            {selectedRec ? <DetailCard rec={selectedRec} selectedCountry={selectedCountry} /> : <div className="no-detail-box">Select a university from the left.</div>}
            {globalAdvice && <GlobalAdviceCard globalAdvice={globalAdvice} />}
          </section>
        </main>

        {compareIds.length > 0 && <CompareDrawer recs={compareRecs} onClear={() => setCompareIds([])} />}

        <button className="bot-fab" onClick={() => setIsBotOpen((v) => !v)} title="Beast Help">
          💬
        </button>
        {isBotOpen && (
          <div className="mini-help">
            Ask: budget / English / SAFE vs AMBITIOUS / how many apply 🙂
          </div>
        )}
      </div>
    );
  };

  if (view === "landing") return renderLanding();
  if (view === "form") return renderProfileForm();
  return renderResults();
}

// ----------------- Detail components -----------------
function DetailCard({ rec, selectedCountry }) {
  const english = rec.english_requirement || {};
  const explain = rec.ai_explainability || null;

  return (
    <div className="detail-card">
      <div className="detail-header">
        <div>
          <div className="detail-uni-name">{rec.university_name}</div>
          <div className="detail-city">
            {rec.city} · {rec.country_name}
          </div>
        </div>

        <div className="detail-badges">
          <span className={`pill level-${rec.level_band}`}>{rec.level_band.toUpperCase()}</span>
          <span className="pill subtle">Fit: {rec.fit_score ?? "?"}/100</span>
          <span className="pill subtle">Admit: {rec.admission_probability ?? "?"}%</span>
          <span className="pill subtle">{rec.tier_label}</span>
          <span className="pill subtle">Visa: {rec.visa_risk || "?"}</span>
        </div>
      </div>

      {selectedCountry === "US" && (
        <div className="detail-section advice-section">
          <h4>US Test Note 🧾</h4>
          <p>Some US programs may require/recommend <b>GRE/GMAT</b>. Always confirm on the official course page.</p>
        </div>
      )}

      <div className="detail-section">
        <h3>Course snapshot 📚</h3>
        <p className="detail-course-name">{rec.course_name}</p>

        <div className="detail-grid">
          <div>
            <div className="label">Subject</div>
            <div>{rec.subject_cluster}</div>
          </div>
          <div>
            <div className="label">Intakes</div>
            <div>{rec.intakes_text}</div>
          </div>
          <div>
            <div className="label">Fees</div>
            <div>
              Tuition {rec.tuition_fee_lakhs}L · Living {rec.estimated_living_lakhs}L · Extras {rec.extra_costs_lakhs}L
            </div>
          </div>
          <div>
            <div className="label">1st year total</div>
            <div>{rec.total_first_year_cost_lakhs}L</div>
          </div>
          <div>
            <div className="label">Math / coding</div>
            <div>
              {rec.math_required ? "Math required" : "Math not strict"}, {rec.coding_required ? "coding required" : "coding not strict"}
            </div>
          </div>
          <div>
            <div className="label">Fit score</div>
            <div>{rec.fit_score ?? "?"}/100</div>
          </div>
          <div>
            <div className="label">Admission probability</div>
            <div>{rec.admission_probability ?? "?"}%</div>
          </div>
        </div>
      </div>

      <div className="detail-section triple">
        <div>
          <h4>Why this university 🏫</h4>
          <ul>{(rec.why_university || []).map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
        <div>
          <h4>Why this course 🎓</h4>
          <ul>{(rec.why_course || []).map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
      </div>

      <div className="detail-section split">
        <div>
          <h4>Pros ✅</h4>
          <ul>{(rec.pros || []).map((p) => <li key={p}>{p}</li>)}</ul>
        </div>
        <div>
          <h4>Cons / cautions ⚠️</h4>
          <ul>{(rec.cons || []).map((c) => <li key={c}>{c}</li>)}</ul>
        </div>
      </div>

      <div className="detail-section">
        <h4>English requirement</h4>
        <p className="english-line">
          IELTS: {english.min_ielts_overall ? `≥ ${english.min_ielts_overall}` : "not specified"} ·
          PTE: {english.min_pte_overall ? `≥ ${english.min_pte_overall}` : "not specified"} ·
          Duolingo: {english.min_duolingo ? `≥ ${english.min_duolingo}` : "not specified"}
        </p>
      </div>

      {rec.short_advice && (
        <div className="detail-section advice-section">
          <h4>Short advice 💡</h4>
          <p>{rec.short_advice}</p>
        </div>
      )}

      {explain && (
        <div className="detail-section">
          <h4>AI explainability 🧠</h4>

          {(explain.key_notes || []).length > 0 && (
            <div className="advice-block">
              <h4>Key reasons</h4>
              <ul>
                {explain.key_notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          )}

          {explain.components_0_to_1 && (
            <div className="advice-block">
              <h4>Score breakdown</h4>
              <ul>
                {Object.entries(explain.components_0_to_1).map(([k, v]) => (
                  <li key={k}>
                    <b>{k}</b>: {Math.round((Number(v) || 0) * 100)}%
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {rec.official_course_url && (
        <div className="detail-section">
          <a href={rec.official_course_url} target="_blank" rel="noreferrer" className="btn primary small">
            🌐 View official course page
          </a>
        </div>
      )}
    </div>
  );
}

function GlobalAdviceCard({ globalAdvice }) {
  return (
    <div className="global-advice-card">
      <h3>Overall guidance 🧭</h3>
      {globalAdvice.headline && <p className="headline">{globalAdvice.headline}</p>}
      {globalAdvice.english_advice && <p className="advice-line">{globalAdvice.english_advice}</p>}
      {globalAdvice.budget_advice && <p className="advice-line">{globalAdvice.budget_advice}</p>}

      {(globalAdvice.profile_gaps || []).length > 0 && (
        <div className="advice-block">
          <h4>Profile gaps</h4>
          <ul>{globalAdvice.profile_gaps.map((g) => <li key={g}>{g}</li>)}</ul>
        </div>
      )}

      {(globalAdvice.next_steps || []).length > 0 && (
        <div className="advice-block">
          <h4>Next steps</h4>
          <ul>{globalAdvice.next_steps.map((n) => <li key={n}>{n}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

function CompareDrawer({ recs, onClear }) {
  if (recs.length === 0) return null;
  return (
    <div className="compare-drawer">
      <div className="compare-header">
        <span>Compare universities ({recs.length}/4 selected)</span>
        <div className="compare-actions">
          <button className="btn ghost small" onClick={onClear}>Clear</button>
        </div>
      </div>

      <div className="compare-grid">
        {recs.map((r) => (
          <div key={r.course_id} className="compare-col">
            <div className="compare-title">
              {r.university_name}
              <span className={`pill level-${r.level_band}`}>{r.level_band.toUpperCase()}</span>
              <span className="pill subtle">Fit {r.fit_score ?? "?"}</span>
              <span className="pill subtle">Admit {r.admission_probability ?? "?"}%</span>
            </div>

            <div className="label">Course</div>
            <div className="value">{r.course_name}</div>

            <div className="label">City / Country</div>
            <div className="value">{r.city} · {r.country_name}</div>

            <div className="label">1st year cost</div>
            <div className="value">{r.total_first_year_cost_lakhs}L</div>

            <div className="label">Intakes</div>
            <div className="value">{r.intakes_text}</div>

            <div className="label">English</div>
            <div className="value">
              IELTS {r.english_requirement?.min_ielts_overall ?? "?"} · PTE {r.english_requirement?.min_pte_overall ?? "?"}
            </div>

            <div className="label">Pros</div>
            <ul className="value">{(r.pros || []).slice(0, 3).map((p) => <li key={p}>{p}</li>)}</ul>

            <div className="label">Cons</div>
            <ul className="value">{(r.cons || []).slice(0, 3).map((c) => <li key={c}>{c}</li>)}</ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;