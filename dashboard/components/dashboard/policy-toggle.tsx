import type { PolicyMode } from "./types";

interface PolicyToggleProps {
  mode: PolicyMode;
}

const policyLabels: Record<PolicyMode, string> = {
  "speed-first": "Speed first",
  "battery-saver": "Battery saver",
  "privacy-first": "Privacy first",
};

export function PolicyToggle({ mode }: PolicyToggleProps) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Policy</p>
        <h2 className="mt-1 text-2xl font-semibold text-white">Routing mode</h2>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-3">
        {Object.entries(policyLabels).map(([key, label]) => {
          const active = key === mode;

          return (
            <button
              key={key}
              type="button"
              className={`rounded-2xl border px-4 py-3 text-left text-sm font-medium transition ${
                active
                  ? "border-cyan-400/40 bg-cyan-400/15 text-white"
                  : "border-white/10 bg-black/20 text-zinc-400 hover:border-white/20 hover:text-zinc-200"
              }`}
              aria-pressed={active}
            >
              <span className="block text-base font-semibold">{label}</span>
              <span className="mt-1 block text-xs uppercase tracking-[0.18em] opacity-70">
                {active ? "Active" : "Available"}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}