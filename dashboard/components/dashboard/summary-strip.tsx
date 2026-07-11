import type { MetricItem } from "./types";

interface SummaryStripProps {
  items: MetricItem[];
}

export function SummaryStrip({ items }: SummaryStripProps) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <article
          key={item.label}
          className="rounded-[24px] border border-white/10 bg-white/5 p-4 shadow-[0_18px_50px_rgba(0,0,0,0.2)] backdrop-blur"
        >
          <p className="text-xs uppercase tracking-[0.24em] text-zinc-400">
            {item.label}
          </p>
          <div className="mt-3 flex items-end justify-between gap-4">
            <span className="text-2xl font-semibold text-white">{item.value}</span>
            <span className="text-right text-xs leading-5 text-zinc-400">
              {item.detail}
            </span>
          </div>
        </article>
      ))}
    </section>
  );
}