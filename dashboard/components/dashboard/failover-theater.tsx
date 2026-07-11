import type { FailoverStory } from "./types";

interface FailoverTheaterProps {
  story: FailoverStory;
}

const storyTone: Record<FailoverStory["status"], string> = {
  ready: "border-sky-400/20 bg-sky-400/10 text-sky-100",
  active: "border-amber-400/20 bg-amber-400/10 text-amber-100",
  resolved: "border-emerald-400/20 bg-emerald-400/10 text-emerald-100",
};

export function FailoverTheater({ story }: FailoverTheaterProps) {
  return (
    <section className={`rounded-[28px] border p-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur ${storyTone[story.status]}`}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] opacity-80">Failover</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Failover theater</h2>
        </div>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-inherit">
          {story.status}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <article className="rounded-[22px] border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">Task</p>
          <p className="mt-2 text-lg font-semibold text-white">{story.task}</p>
        </article>
        <article className="rounded-[22px] border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">Migrating from</p>
          <p className="mt-2 text-lg font-semibold text-white">{story.fromDevice}</p>
        </article>
        <article className="rounded-[22px] border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">Migrating to</p>
          <p className="mt-2 text-lg font-semibold text-white">{story.toDevice}</p>
        </article>
      </div>

      <p className="mt-4 text-sm leading-6 opacity-90">{story.reason}</p>
    </section>
  );
}