// src/components/CountryCard.jsx
import React from "react";

export default function CountryCard({ country, selected, onSelect }) {
  const { code, name, flag, tagline, bullets = [] } = country;

  return (
    <button
      type="button"
      onClick={() => onSelect(code)}
      className={`group relative flex flex-col overflow-hidden rounded-2xl border px-4 py-4 text-left transition
      ${
        selected
          ? "border-emerald-400/80 bg-slate-900/80 shadow-[0_0_30px_-15px] shadow-emerald-400/80"
          : "border-slate-800 bg-slate-900/60 hover:border-emerald-400/60 hover:bg-slate-900"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800 text-2xl">
            {flag}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">{name}</h2>
              {code !== "COMING" && selected && (
                <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-medium text-emerald-300">
                  Selected
                </span>
              )}
              {code === "COMING" && (
                <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] font-medium text-slate-400">
                  Coming soon
                </span>
              )}
            </div>
            {tagline && (
              <p className="text-[11px] text-slate-400">{tagline}</p>
            )}
          </div>
        </div>
      </div>

      {bullets.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-400">
          {bullets.map((b, idx) => (
            <li key={idx} className="flex items-center gap-1">
              <span className="h-1 w-1 rounded-full bg-slate-500" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}
    </button>
  );
}
