// src/components/UniversityModal.jsx
import React from "react";

export default function UniversityModal({ item, onClose }) {
  if (!item) return null;

  const english = item.english_requirement || {};

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-3">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-3xl border border-slate-800 bg-slate-950/95 p-5 shadow-2xl shadow-black">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="text-lg">{item.country_code === "UK" ? "🇬🇧" : item.country_code === "US" ? "🇺🇸" : "🎓"}</span>
              <span>{item.country_name}</span>
              <span className="h-0.5 w-4 rounded-full bg-slate-600" />
              <span>{item.city}</span>
            </div>
            <h2 className="mt-1 text-lg font-semibold">
              {item.university_name}
            </h2>
            <p className="text-sm text-slate-300">{item.course_name}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300 hover:bg-slate-700"
          >
            Close
          </button>
        </div>

        <div className="mb-4 grid gap-3 md:grid-cols-3 text-xs">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              Cost & budget
            </p>
            <p className="text-slate-400">
              Fees: <span className="text-slate-100">{item.tuition_fee_lakhs}L</span>
            </p>
            <p className="text-slate-400">
              Living:{" "}
              <span className="text-slate-100">
                {item.estimated_living_lakhs}L
              </span>
            </p>
            {item.extra_costs_lakhs > 0 && (
              <p className="text-slate-400">
                Extras:{" "}
                <span className="text-slate-100">
                  {item.extra_costs_lakhs}L
                </span>
              </p>
            )}
            <p className="mt-1 text-slate-300">
              Avg 1st year:{" "}
              <span className="font-semibold">
                {item.total_first_year_cost_lakhs}L
              </span>{" "}
              ({item.budget_label})
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              Academics & visa
            </p>
            <p className="text-slate-400">
              Level: <span className="text-slate-100">{item.level_band}</span>
            </p>
            <p className="text-slate-400">
              Visa risk:{" "}
              <span className="text-slate-100">{item.visa_risk}</span>
            </p>
            <p className="text-slate-400">
              Type: <span className="text-slate-100">{item.tier_label}</span>
            </p>
            <p className="mt-1 text-slate-400">
              Intakes:{" "}
              <span className="text-slate-100">{item.intakes_text}</span>
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              English requirement
            </p>
            <ul className="space-y-0.5 text-slate-400">
              {english.min_ielts_overall && (
                <li>IELTS ≥ {english.min_ielts_overall}</li>
              )}
              {english.min_pte_overall && (
                <li>PTE ≥ {english.min_pte_overall}</li>
              )}
              {english.min_duolingo && (
                <li>Duolingo ≥ {english.min_duolingo}</li>
              )}
              {english.inter_english_ok && english.country_allows_inter && (
                <li>Inter English accepted (country rules allow).</li>
              )}
            </ul>
            <p className="mt-1 text-[11px] text-slate-400">
              Match now:{" "}
              <span className="font-medium text-slate-100">
                {english.english_ok_now ? "OK" : "Gap – improve score."}
              </span>
            </p>
          </div>
        </div>

        <div className="mb-4 grid gap-3 md:grid-cols-2 text-xs">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              Pros
            </p>
            <ul className="space-y-1 text-slate-400">
              {(item.pros || []).map((p, idx) => (
                <li key={idx} className="flex items-start gap-1">
                  <span className="mt-1 h-1 w-1 rounded-full bg-emerald-400" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              Cons / cautions
            </p>
            <ul className="space-y-1 text-slate-400">
              {(item.cons || []).map((c, idx) => (
                <li key={idx} className="flex items-start gap-1">
                  <span className="mt-1 h-1 w-1 rounded-full bg-rose-400" />
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {item.short_advice && (
          <div className="mb-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-xs text-slate-300">
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              Our advice for you
            </p>
            <p>{item.short_advice}</p>
          </div>
        )}

        {item.official_course_url && (
          <a
            href={item.official_course_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-900 hover:bg-white"
          >
            Open official course page ↗
          </a>
        )}
      </div>
    </div>
  );
}
