// src/components/ChatBox.jsx
import React, { useState } from "react";

export default function ChatBox({ stats, globalAdvice, lastProfile }) {
  const [open, setOpen] = useState(true);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      from: "bot",
      text: "Hi! I’m a small rules-based helper. Ask me about IELTS, budget, safe vs ambitious options, or intakes.",
    },
  ]);

  const safe = stats?.safe_count ?? 0;
  const moderate = stats?.moderate_count ?? 0;
  const ambitious = stats?.ambitious_count ?? 0;

  const send = (text) => {
    if (!text.trim()) return;
    const userMsg = { from: "you", text: text.trim() };
    setMessages((m) => [...m, userMsg]);

    // Simple rule-based reply using globalAdvice + stats
    let reply = "I’m using only offline rules now.";

    const lower = text.toLowerCase();
    if (lower.includes("ielts") || lower.includes("english")) {
      reply =
        globalAdvice?.english_advice ||
        "English scores matter a lot. If you don't have IELTS/PTE yet, plan to take one in the next 1–3 months.";
    } else if (lower.includes("budget")) {
      reply =
        globalAdvice?.budget_advice ||
        "Your budget seems reasonable for at least a few options. Cheaper cities and teaching-focused universities reduce cost.";
    } else if (lower.includes("safe") || lower.includes("ambitious")) {
      reply = `Right now I see approx ${safe} safe, ${moderate} moderate and ${ambitious} ambitious options in your last search. Mix 2–3 safe with 1–2 ambitious when you apply.`;
    } else if (lower.includes("intake") || lower.includes("deadline")) {
      reply =
        globalAdvice?.next_steps?.[0] ||
        "For most countries you should start applications at least 8–10 months before intake and track deadlines carefully.";
    } else {
      reply =
        globalAdvice?.headline ||
        "Use the left form to run a search first. Then I can talk about your profile using those results.";
    }

    const botMsg = { from: "bot", text: reply };
    setMessages((m) => [...m, botMsg]);
    setInput("");
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-20 rounded-full bg-emerald-500 px-4 py-2 text-xs font-medium text-slate-950 shadow-lg shadow-emerald-500/50"
      >
        Ask Beast Counsellor
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-20 w-72 rounded-2xl border border-slate-800 bg-slate-950/95 shadow-2xl shadow-black">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <div>
          <p className="text-[11px] font-semibold text-slate-100">
            Mini Help Bot (offline rules)
          </p>
          <p className="text-[10px] text-slate-500">
            Not real AI yet – using your last search results.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-full bg-slate-800 px-2 py-1 text-[10px] text-slate-300 hover:bg-slate-700"
        >
          ✕
        </button>
      </div>

      <div className="flex max-h-72 flex-col">
        <div className="flex-1 space-y-2 overflow-y-auto px-3 py-2 text-[11px]">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${
                m.from === "you" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-3 py-1.5 ${
                  m.from === "you"
                    ? "bg-emerald-500 text-slate-950"
                    : "bg-slate-800 text-slate-100"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-slate-800 px-2 py-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-1"
          >
            <input
              className="flex-1 rounded-xl border border-slate-700 bg-slate-900/80 px-2 py-1.5 text-[11px] text-slate-100 outline-none focus:border-emerald-400"
              placeholder="Ask about IELTS, budget, or safe options…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button
              type="submit"
              className="rounded-xl bg-emerald-500 px-3 py-1.5 text-[11px] font-medium text-slate-950"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
