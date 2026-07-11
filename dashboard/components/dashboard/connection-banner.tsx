import type { ConnectionState } from "./types";

interface ConnectionBannerProps {
  state: ConnectionState;
  message: string;
}

const bannerStyles: Record<ConnectionState, string> = {
  connected: "border-emerald-400/20 bg-emerald-400/10 text-emerald-100",
  reconnecting: "border-amber-400/20 bg-amber-400/10 text-amber-100",
  disconnected: "border-rose-400/20 bg-rose-400/10 text-rose-100",
};

export function ConnectionBanner({ state, message }: ConnectionBannerProps) {
  return (
    <section className={`mb-4 rounded-[24px] border px-4 py-3 text-sm shadow-[0_18px_50px_rgba(0,0,0,0.18)] backdrop-blur ${bannerStyles[state]}`}>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-semibold uppercase tracking-[0.24em]">Connection</span>
        <span className="text-xs opacity-80">Auto-reconnect ready</span>
      </div>
      <p className="mt-2 leading-6 opacity-90">{message}</p>
    </section>
  );
}