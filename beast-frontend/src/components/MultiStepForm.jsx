// src/components/MultiStepForm.jsx
import React, { useState } from "react";

const clusterOptions = [
  { id: "data_science", label: "MSc Data Science" },
  { id: "ai_ml", label: "MSc AI / ML" },
  { id: "cs_software", label: "MSc CS / Software" },
  { id: "business_analytics", label: "MSc Business / Data Analytics" },
  { id: "cyber_security", label: "MSc Cyber Security" },
  { id: "mba", label: "MBA" },
  { id: "cloud_it", label: "MSc Cloud / IT / IS" },
  { id: "project_mgmt", label: "MSc Project Management" },
];

export default function MultiStepForm({
  selectedCountry,
  onSearch,
  loading,
  lastError,
}) {
  const [step, setStep] = useState(1);

  const [name, setName] = useState("sidhu");
  const [cgpa, setCgpa] = useState("8.2");
  const [backlogs, setBacklogs] = useState("0");
  const [workEx, setWorkEx] = useState("0");
  const [budget, setBudget] = useState("35");
  const [englishType, setEnglishType] = useState("inter");
  const [englishScore, setEnglishScore] = useState("70");
  const [intake, setIntake] = useState("Sep 2026");
  const [selectedClusters, setSelectedClusters] = useState(["data_science"]);
  const [requestedCount, setRequestedCount] = useState("7");

  const toggleCluster = (id) => {
    setSelectedClusters((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedCountry) return;

    const payload = {
      name,
      country_code: selectedCountry.code,
      cgpa: parseFloat(cgpa || "0"),
      backlogs_count: parseInt(backlogs || "0", 10),
      work_ex_years: parseFloat(workEx || "0"),
      budget_lakhs: parseFloat(budget || "0"),
      english_proof_type: englishType,
      english_score: parseFloat(englishScore || "0"),
      target_intake: intake,
      subject_clusters: selectedClusters,
      requested_count: parseInt(requestedCount || "7", 10),
      non_math_background: false,
    };

    onSearch(payload);
  };

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/40">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Student profile</h2>
          <p className="text-xs text-slate-400">
            Fill honestly – the engine is strict, it won&apos;t lie.
          </p>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-slate-400">
          <span
            className={`h-1.5 w-6 rounded-full ${
              step === 1 ? "bg-emerald-400" : "bg-slate-700"
            }`}
          />
          <span
            className={`h-1.5 w-6 rounded-full ${
              step === 2 ? "bg-emerald-400" : "bg-slate-700"
            }`}
          />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        {/* Step 1: academics + budget */}
        {step === 1 && (
          <>
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  Your name
                </label>
                <input
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  CGPA
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={cgpa}
                  onChange={(e) => setCgpa(e.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  Any backlogs?
                </label>
                <input
                  type="number"
                  min="0"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={backlogs}
                  onChange={(e) => setBacklogs(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  Total work-ex (years)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={workEx}
                  onChange={(e) => setWorkEx(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  Budget 1st year (in lakhs)
                </label>
                <input
                  type="number"
                  min="0"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                />
              </div>
            </div>
          </>
        )}

        {/* Step 2: english + course */}
        {step === 2 && (
          <>
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  English proof
                </label>
                <select
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={englishType}
                  onChange={(e) => setEnglishType(e.target.value)}
                >
                  <option value="ielts">IELTS</option>
                  <option value="pte">PTE</option>
                  <option value="duolingo">Duolingo</option>
                  <option value="inter">Inter English</option>
                  <option value="medium">Medium of Instruction</option>
                  <option value="none">No test yet</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  Score / %
                </label>
                <input
                  type="number"
                  step="0.5"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={englishScore}
                  onChange={(e) => setEnglishScore(e.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  Preferred intake (e.g. Sep 2026)
                </label>
                <input
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={intake}
                  onChange={(e) => setIntake(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  How many universities? (max 10)
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs outline-none focus:border-emerald-400"
                  value={requestedCount}
                  onChange={(e) => setRequestedCount(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-[11px] text-slate-400">
                Choose course clusters
              </label>
              <div className="grid gap-2 md:grid-cols-2">
                {clusterOptions.map((c) => {
                  const active = selectedClusters.includes(c.id);
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleCluster(c.id)}
                      className={`flex items-center justify-between rounded-xl border px-3 py-2 text-[11px] transition ${
                        active
                          ? "border-emerald-400 bg-emerald-500/10 text-emerald-100"
                          : "border-slate-700 bg-slate-900/80 text-slate-300 hover:border-slate-500"
                      }`}
                    >
                      <span>{c.label}</span>
                      {active && (
                        <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      )}
                    </button>
                  );
                })}
              </div>
              <p className="mt-2 text-[10px] text-slate-500">
                Example: for Data + AI, select Data Science + AI / ML. For mixed
                profile, select 2–3 clusters.
              </p>
            </div>
          </>
        )}

        <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3">
          <div className="text-[10px] text-slate-500">
            {lastError ? (
              <span className="text-rose-400">{lastError}</span>
            ) : selectedCountry ? (
              <span>
                Country: <span className="font-medium">{selectedCountry.name}</span>{" "}
                ({selectedCountry.flag}) · Engine will also try to show 1 dream
                option when possible.
              </span>
            ) : (
              "Select a country above to start."
            )}
          </div>
          <div className="flex items-center gap-2">
            {step === 2 && (
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-[11px] text-slate-200 hover:border-slate-500"
              >
                Back
              </button>
            )}
            {step === 1 && (
              <button
                type="button"
                onClick={() => setStep(2)}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-[11px] text-slate-200 hover:border-slate-500"
              >
                Next
              </button>
            )}
            {step === 2 && (
              <button
                type="submit"
                disabled={loading || !selectedCountry}
                className="flex items-center gap-1 rounded-xl bg-emerald-500 px-4 py-1.5 text-[11px] font-medium text-slate-950 shadow-lg shadow-emerald-500/40 disabled:cursor-not-allowed disabled:bg-emerald-500/60"
              >
                {loading ? "Finding..." : "Find universities"}
              </button>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}
