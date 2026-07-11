import type { DecisionLogEntry } from "./types";

interface DecisionLogProps {
  entries: DecisionLogEntry[];
}

const toneStyles: Record<DecisionLogEntry["tone"], string> = {
  info: "border-sky-400/20 bg-sky-400/10 text-sky-100",
  success: "border-emerald-400/20 bg-emerald-400/10 text-emerald-100",
  warning: "border-amber-400/20 bg-amber-400/10 text-amber-100",
  critical: "border-rose-400/20 bg-rose-400/10 text-rose-100",
};

export function DecisionLog({ entries }: DecisionLogProps) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Trace</p>
        <h2 className="mt-1 text-2xl font-semibold text-white">Decision log</h2>
      </div>

      <div className="mt-5 space-y-3">
        {entries.map((entry) => (
          <article key={entry.id} className={`rounded-[22px] border p-4 ${toneStyles[entry.tone]}`}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] opacity-70">{entry.timestamp}</p>
                <h3 className="mt-1 text-lg font-semibold text-white">{entry.task}</h3>
              </div>
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-inherit">
                {entry.device}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-inherit opacity-90">{entry.reason}</p>
          </article>
        ))}
      </div>
    </section>
  );
}