"use client";

import type { DagEdge, DagNode } from "./types";

interface WorkflowDagProps {
  nodes: DagNode[];
  edges: DagEdge[];
}

const nodeStyles: Record<DagNode["status"], string> = {
  pending: "border-white/10 bg-white/5 text-zinc-300",
  running: "border-cyan-400/30 bg-cyan-400/15 text-cyan-100",
  complete: "border-emerald-400/30 bg-emerald-400/15 text-emerald-100",
  failed: "border-rose-400/30 bg-rose-400/15 text-rose-100",
};

export function WorkflowDag({ nodes, edges }: WorkflowDagProps) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_22px_80px_rgba(0,0,0,0.24)] backdrop-blur">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Workflow</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Decision DAG</h2>
        </div>
        <p className="text-sm text-zinc-400">Structured now for future live animation and rerouting states.</p>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {nodes.map((node) => (
          <article
            key={node.id}
            className={`rounded-[22px] border p-4 shadow-[0_16px_40px_rgba(0,0,0,0.2)] ${nodeStyles[node.status]}`}
          >
            <p className="text-xs uppercase tracking-[0.22em] opacity-70">{node.id}</p>
            <h3 className="mt-2 text-lg font-semibold text-white">{node.label}</h3>
            <div className="mt-3 flex items-center justify-between text-xs text-inherit opacity-80">
              <span>{node.deviceId ?? "unassigned"}</span>
              <span>{node.status}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {edges.map((edge) => (
          <div
            key={`${edge.from}-${edge.to}`}
            className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-zinc-300"
          >
            {edge.from} → {edge.to}
            {edge.label ? <span className="text-zinc-500"> · {edge.label}</span> : null}
          </div>
        ))}
      </div>
    </section>
  );
}