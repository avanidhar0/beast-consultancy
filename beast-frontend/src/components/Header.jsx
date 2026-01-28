// src/components/Header.jsx
import React from "react";

export default function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500 text-lg font-bold text-slate-950 shadow-lg shadow-emerald-500/40">
            B
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Beast Consultancy
            </h1>
            <p className="text-xs text-slate-400">
              Strict, realistic admissions engine – using your own offline DB
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-3 py-1 text-emerald-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Offline rules · No API keys
          </span>
        </div>
      </div>
    </header>
  );
}
