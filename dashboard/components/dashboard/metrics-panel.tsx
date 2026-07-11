"use client";

import type { MetricItem } from "./types";

interface MetricsPanelProps {
  metrics: MetricItem[];
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Metrics</p>
        <h2 className="mt-1 text-2xl font-semibold text-white">Performance snapshot</h2>
      </div>

      <div className="mt-5 space-y-3">
        {metrics.map((metric) => (
          <article key={metric.label} className="rounded-[22px] border border-white/10 bg-black/20 p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm font-medium text-zinc-300">{metric.label}</p>
              <span className="text-lg font-semibold text-white">{metric.value}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-zinc-400">{metric.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}