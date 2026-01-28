// src/components/UniversityCard.jsx
import React from "react";

const levelColors = {
  safe: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  moderate: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  ambitious: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  unknown: "bg-slate-700 text-slate-200 border-slate-600",
};

export default function UniversityCard({
  item,
  index,
  onViewDetails,
  onToggleCompare,
  selectedForCompare,
}) {
  const levelColor = levelColors[item.level_band] || levelColors.unknown;
  const isSelected = selectedForCompare.some(
    (c) => c.course_id === item.course_id
  );

  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 text-xs shadow-lg shadow-slate-950/40">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500">
              {index + 1}.
            </span>
            <h3 className="text-sm font-semibold leading-snug">
              {item.university_name} – {item.city}
            </h3>
          </div>
          <p className="mt-0.5 text-[11px] text-slate-300">
            {item.course_name}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] ${levelColor}`}
          >
            Level: {item.level_band || "unknown"}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] text-slate-300">
            Visa: {item.visa_risk || "N/A"}
          </span>
        </div>
      </div>

      <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
        <span>
          Fees: <span className="text-slate-200">{item.tuition_fee_lakhs}L</span>
        </span>
        <span>
          Living:{" "}
          <span className="text-slate-200">{item.estimated_living_lakhs}L</span>
        </span>
        {item.extra_costs_lakhs > 0 && (
          <span>
            Extras:{" "}
            <span className="text-slate-200">{item.extra_costs_lakhs}L</span>
          </span>
        )}
        <span>
          Avg total:{" "}
          <span className="font-medium text-slate-50">
            {item.total_first_year_cost_lakhs}L
          </span>
        </span>
        <span className="ml-auto text-[10px] text-slate-500">
          Intakes: {item.intakes_text}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="mb-1 text-[10px] font-semibold text-slate-300">Pros</p>
          <ul className="space-y-0.5 text-[10px] text-slate-400">
            {(item.pros || []).slice(0, 3).map((p, idx) => (
              <li key={idx} className="flex items-start gap-1">
                <span className="mt-1 h-1 w-1 rounded-full bg-emerald-400" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-[10px] font-semibold text-slate-300">
            Cons / cautions
          </p>
          <ul className="space-y-0.5 text-[10px] text-slate-400">
            {(item.cons || []).slice(0, 3).map((c, idx) => (
              <li key={idx} className="flex items-start gap-1">
                <span className="mt-1 h-1 w-1 rounded-full bg-rose-400" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-2">
        <button
          type="button"
          onClick={() => onViewDetails(item)}
          className="text-[11px] font-medium text-emerald-300 hover:text-emerald-200"
        >
          View full details
        </button>
        <label className="flex cursor-pointer items-center gap-1 text-[11px] text-slate-300">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleCompare(item)}
            className="h-3 w-3 rounded border-slate-600 bg-slate-900 text-emerald-500"
          />
          <span>Compare</span>
        </label>
      </div>
    </article>
  );
}
