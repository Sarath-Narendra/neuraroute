"use client";

interface DashboardHeaderProps {
  title: string;
  subtitle: string;
}

export function DashboardHeader({
  title,
  subtitle,
}: DashboardHeaderProps) {
  return (
    <header className="mb-4 flex flex-col gap-4 rounded-[28px] border border-white/10 bg-white/5 px-5 py-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur xl:flex-row xl:items-end xl:justify-between xl:px-8">
      <div className="space-y-3">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            {title}
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-zinc-300 sm:text-base">
            {subtitle}
          </p>
        </div>
      </div>

    </header>
  );
}