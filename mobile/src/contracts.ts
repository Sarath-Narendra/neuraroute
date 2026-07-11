/**
 * NeuraRoute wire contracts (v2) — the event shape streamed over the engine /ws.
 * Ported from the shelved web dashboard's contracts.ts; only what the phone app needs.
 */

export type Severity = "normal" | "mild" | "emergency";

export type NeuraRouteEventType =
  | "device_alive"
  | "device_stale"
  | "request_start"
  | "placement"
  | "task_start"
  | "task_done"
  | "failover"
  | "metrics"
  | "request_done"
  | "policy"
  | "sos";

export interface Vitals {
  hr?: number;
  spo2?: number;
  temp_c?: number;
  resp_rate?: number;
  bp_sys?: number;
  bp_dia?: number;
  [k: string]: number | undefined;
}

export interface TriageResult {
  op?: string;
  patient_id?: string;
  severity?: Severity;
  transcript?: string;
}

export interface NeuraRouteEvent {
  type: NeuraRouteEventType;
  ts: number;
  request_id?: string;
  task_id?: string;
  device_id?: string;
  from_device?: string;
  op?: string;
  reason?: string;
  patient_id?: string;
  vitals?: Vitals;
  severity?: Severity;
  result?: TriageResult;
  source?: string;
  metrics?: Record<string, unknown>;
  heartbeat?: Record<string, unknown>;
}

/** The four tiers of the connectivity ladder, in priority order. */
export const LADDER: { id: string; label: string; short: string }[] = [
  { id: "cloud-01", label: "GPT (cloud)", short: "Cloud" },
  { id: "pc-01", label: "PC (local LLM)", short: "PC" },
  { id: "phone-01", label: "Phone (local LLM)", short: "Phone" },
  { id: "arduino-01", label: "Arduino (SLM)", short: "Uno Q" },
];

export const TIER_LABEL: Record<string, string> = Object.fromEntries(
  LADDER.map((t) => [t.id, t.label]),
);

export const SEVERITY_RANK: Record<Severity, number> = {
  normal: 0,
  mild: 1,
  emergency: 2,
};
