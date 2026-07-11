import type { ConnectionState } from "./types";

interface DashboardHeaderProps {
  title: string;
  subtitle: string;
  connectionState: ConnectionState;
  connectionCopy: string;
}

const stateStyles: Record<ConnectionState, string> = {
  connected: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  reconnecting: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  disconnected: "border-rose-400/30 bg-rose-400/10 text-rose-200",
};

export function DashboardHeader({
  title,
  subtitle,
  connectionState,
  connectionCopy,
}: DashboardHeaderProps) {
  return (
    <header className="mb-4 flex flex-col gap-4 rounded-[28px] border border-white/10 bg-white/5 px-5 py-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur xl:flex-row xl:items-end xl:justify-between xl:px-8">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.3em] text-cyan-100">
          NeuraRoute dashboard
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            {title}
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-zinc-300 sm:text-base">
            {subtitle}
          </p>
        </div>
      </div>

      <div className="flex flex-col items-start gap-3 xl:items-end">
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] ${stateStyles[connectionState]}`}>
          {connectionState}
        </span>
        <p className="max-w-sm text-right text-sm text-zinc-400">{connectionCopy}</p>
      </div>
    </header>
  );
}