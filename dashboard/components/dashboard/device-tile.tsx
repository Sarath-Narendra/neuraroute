import type { DashboardDevice } from "./types";

interface DeviceTileProps {
  device: DashboardDevice;
}

const statusStyles: Record<DashboardDevice["status"], string> = {
  online: "border-emerald-400/25 bg-emerald-400/10 text-emerald-100",
  busy: "border-sky-400/25 bg-sky-400/10 text-sky-100",
  failover: "border-amber-400/25 bg-amber-400/10 text-amber-100",
  offline: "border-rose-400/25 bg-rose-400/10 text-rose-100",
};

function Bar({ value, accent }: { value: number; accent: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-full rounded-full ${accent}`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function DeviceTile({ device }: DeviceTileProps) {
  return (
    <article className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,_rgba(255,255,255,0.07),_rgba(255,255,255,0.03))] p-4 shadow-[0_18px_50px_rgba(0,0,0,0.24)] backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-zinc-300">{device.kind}</p>
          <h3 className="mt-1 text-xl font-semibold text-white">{device.name}</h3>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${statusStyles[device.status]}`}>
          {device.status}
        </span>
      </div>

      <div className="mt-4 space-y-3 text-sm text-zinc-300">
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span>Battery</span>
            <span>{device.battery}%</span>
          </div>
          <Bar value={device.battery} accent="bg-gradient-to-r from-emerald-400 to-cyan-300" />
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span>CPU</span>
            <span>{device.cpuLoad}%</span>
          </div>
          <Bar value={device.cpuLoad} accent="bg-gradient-to-r from-sky-400 to-indigo-400" />
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span>NPU</span>
            <span>{device.npuLoad}%</span>
          </div>
          <Bar value={device.npuLoad} accent="bg-gradient-to-r from-fuchsia-400 to-pink-400" />
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3 text-xs text-zinc-400">
        {device.activeTask ? (
          <span>Running {device.activeTask}</span>
        ) : (
          <span>Standing by for routed work</span>
        )}
      </div>
    </article>
  );
}