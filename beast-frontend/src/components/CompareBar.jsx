// src/components/CompareBar.jsx
import React, { useState } from "react";

export default function CompareBar({ items, onRemove }) {
  const [open, setOpen] = useState(false);

  if (!items || items.length === 0) return null;

  return (
    <>
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-slate-400">
              Comparing {items.length} universit{items.length === 1 ? "y" : "ies"}:
            </span>
            {items.map((c) => (
              <button
                key={c.course_id}
                type="button"
                onClick={() => onRemove(c)}
                className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] text-slate-200 hover:bg-slate-700"
              >
                {c.country_code} · {c.university_name.split(" ")[0]} ·{" "}
                {c.total_first_year_cost_lakhs}L
                <span className="text-slate-500">✕</span>
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-xl bg-emerald-500 px-3 py-1.5 text-[11px] font-medium text-slate-950 shadow-lg shadow-emerald-500/40"
          >
            Open comparison
          </button>
        </div>
      </div>

      {open && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/75 p-3">
          <div className="max-h-[90vh] w-full max-w-6xl overflow-x-auto rounded-3xl border border-slate-800 bg-slate-950/95 p-4 shadow-2xl shadow-black text-xs">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Compare universities</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-full bg-slate-800 px-3 py-1 text-[11px] text-slate-200 hover:bg-slate-700"
              >
                Close
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse text-[11px]">
                <thead>
                  <tr>
                    <th className="border-b border-slate-800 px-2 py-2 text-left text-slate-400">
                      Field
                    </th>
                    {items.map((c) => (
                      <th
                        key={c.course_id}
                        className="border-b border-slate-800 px-2 py-2 text-left text-slate-200"
                      >
                        <div className="text-[11px] font-semibold">
                          {c.university_name}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {c.course_name}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="align-top">
                  {[
                    ["Country / city", (c) => `${c.country_name} · ${c.city}`],
                    ["Level", (c) => c.level_band],
                    ["Visa risk", (c) => c.visa_risk],
                    ["Type", (c) => c.tier_label],
                    [
                      "Avg 1st year cost",
                      (c) => `${c.total_first_year_cost_lakhs} L`,
                    ],
                    [
                      "Fees / Living / Extras",
                      (c) =>
                        `${c.tuition_fee_lakhs}L / ${c.estimated_living_lakhs}L / ${c.extra_costs_lakhs}L`,
                    ],
                    ["Budget fit", (c) => c.budget_label],
                    ["Intakes", (c) => c.intakes_text],
                    [
                      "Math / Coding",
                      (c) =>
                        `${c.math_required ? "Maths" : "No strict maths"}, ${
                          c.coding_required ? "Coding" : "No strict coding"
                        }`,
                    ],
                    [
                      "Typical scholarship",
                      (c) =>
                        c.typical_scholarship_lakhs
                          ? `${c.typical_scholarship_lakhs}L`
                          : "N/A",
                    ],
                  ].map(([label, fn]) => (
                    <tr key={label}>
                      <td className="border-b border-slate-900 px-2 py-1 text-slate-400">
                        {label}
                      </td>
                      {items.map((c) => (
                        <td
                          key={c.course_id + label}
                          className="border-b border-slate-900 px-2 py-1 text-slate-200"
                        >
                          {fn(c)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
