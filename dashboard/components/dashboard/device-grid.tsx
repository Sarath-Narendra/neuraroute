import { DeviceTile } from "./device-tile";
import type { DashboardDevice } from "./types";

interface DeviceGridProps {
  devices: DashboardDevice[];
}

export function DeviceGrid({ devices }: DeviceGridProps) {
  return (
    <section className="space-y-4 rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Devices</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Live device tiles</h2>
        </div>
        <p className="text-sm text-zinc-400">Battery, CPU, NPU, and task state update from engine events.</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-4">
        {devices.map((device) => (
          <DeviceTile key={device.id} device={device} />
        ))}
      </div>
    </section>
  );
}