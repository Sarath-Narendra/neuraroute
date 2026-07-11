"use client";

import { useState } from "react";

import { DeviceGrid } from "./device-grid";
import type { DashboardDevice } from "./types";

interface DeviceStateWindowProps {
  devices: DashboardDevice[];
}

const statusStyles: Record<DashboardDevice["status"], string> = {
  online: "border-emerald-400/25 bg-emerald-400/10 text-emerald-100",
  busy: "border-cyan-400/25 bg-cyan-400/10 text-cyan-100",
  failover: "border-amber-400/25 bg-amber-400/10 text-amber-100",
  offline: "border-rose-400/25 bg-rose-400/10 text-rose-100",
};

export function DeviceStateWindow({ devices }: DeviceStateWindowProps) {
  const [isMaximized, setIsMaximized] = useState(false);
  const maximizedDevices = devices.filter((device) => device.id !== "surface");

  return (
    <section className="rounded-[28px] border border-white/10 bg-white/5 px-5 py-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-linear-to-r from-cyan-300/50 via-white/10 to-transparent" />
        <div className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.26em] text-cyan-100">
          Connected window
        </div>
        <button
          type="button"
          onClick={() => setIsMaximized((currentValue) => !currentValue)}
          className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs font-medium uppercase tracking-[0.22em] text-zinc-200 transition hover:border-cyan-300/30 hover:bg-cyan-300/10"
        >
          {isMaximized ? "Minimize" : "Maximize"}
        </button>
        <div className="h-px flex-1 bg-linear-to-l from-cyan-300/50 via-white/10 to-transparent" />
      </div>

      {!isMaximized ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {devices.map((device) => (
            <article
              key={device.id}
              className={`rounded-[20px] border px-4 py-3 text-sm shadow-[0_12px_30px_rgba(0,0,0,0.14)] ${statusStyles[device.status]}`}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-white">{device.name}</p>
                <span className="text-xs uppercase tracking-[0.2em] opacity-80">{device.status}</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {isMaximized ? (
        <div className="mt-5 rounded-[28px] border border-white/10 bg-black/10 p-5 shadow-[0_18px_50px_rgba(0,0,0,0.18)]">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Devices</p>
              <h2 className="mt-1 text-2xl font-semibold text-white">Live device tiles</h2>
            </div>
            <p className="text-sm text-zinc-400">Battery, CPU, NPU, and task state update from engine events.</p>
          </div>

          <div className="mt-4">
            <DeviceGrid devices={maximizedDevices} />
          </div>
        </div>
      ) : null}
    </section>
  );
}