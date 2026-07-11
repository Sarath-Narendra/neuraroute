/**
 * Pure reducer over the NeuraRoute event stream. Ported/adapted from the shelved web
 * dashboard's applyEventToSnapshot. Produces the state the phone UI renders.
 */
import { LADDER, NeuraRouteEvent, Severity, Vitals } from "./contracts";

export interface PatientState {
  patient_id: string;
  name?: string;
  age?: number;
  conditions?: string[];
  severity?: Severity;
  transcript?: string;
  vitals?: Vitals;
  tier?: string; // device_id that produced the latest verdict
  status: "idle" | "analyzing";
  updatedAt?: number;
  emergencyReason?: string; // set while an SOS for this patient is unacknowledged
}

export interface TierState {
  id: string;
  alive: boolean;
  lastSeen?: number;
}

export interface ActivityEntry {
  id: string;
  ts: number;
  text: string;
  tone: "info" | "success" | "warning" | "critical";
}

export interface AppState {
  patients: Record<string, PatientState>;
  order: string[]; // patient display order
  tiers: Record<string, TierState>;
  activity: ActivityEntry[];
  /** Monotonic marker set when a NEW sos arrives, so the hook can fire a notification. */
  lastSos?: { patient_id: string; reason: string; ts: number; seq: number };
}

export function initialState(): AppState {
  const tiers: Record<string, TierState> = {};
  for (const t of LADDER) tiers[t.id] = { id: t.id, alive: false };
  return { patients: {}, order: [], tiers, activity: [] };
}

/** Seed patient cards from GET /patients so all 10 show before any reading arrives. */
export function seedRoster(
  state: AppState,
  roster: Array<{ patient_id: string; name?: string; age?: number; conditions?: string[] }>,
): AppState {
  const patients = { ...state.patients };
  const order = [...state.order];
  for (const p of roster) {
    if (!patients[p.patient_id]) {
      patients[p.patient_id] = {
        patient_id: p.patient_id,
        name: p.name,
        age: p.age,
        conditions: p.conditions,
        status: "idle",
      };
      order.push(p.patient_id);
    }
  }
  return { ...state, patients, order };
}

let SEQ = 0;

function pushActivity(state: AppState, entry: ActivityEntry): ActivityEntry[] {
  return [entry, ...state.activity].slice(0, 40);
}

function ensurePatient(state: AppState, id: string): { patients: Record<string, PatientState>; order: string[] } {
  if (state.patients[id]) return { patients: state.patients, order: state.order };
  return {
    patients: { ...state.patients, [id]: { patient_id: id, status: "idle" } },
    order: [...state.order, id],
  };
}

export function applyEvent(state: AppState, e: NeuraRouteEvent): AppState {
  switch (e.type) {
    case "device_alive": {
      if (!e.device_id) return state;
      return {
        ...state,
        tiers: { ...state.tiers, [e.device_id]: { id: e.device_id, alive: true, lastSeen: e.ts } },
      };
    }
    case "device_stale": {
      if (!e.device_id) return state;
      const prev = state.tiers[e.device_id];
      return {
        ...state,
        tiers: { ...state.tiers, [e.device_id]: { id: e.device_id, alive: false, lastSeen: prev?.lastSeen } },
        activity: pushActivity(state, {
          id: `${e.type}-${e.device_id}-${e.ts}`,
          ts: e.ts,
          text: `${e.device_id} went offline`,
          tone: "warning",
        }),
      };
    }
    case "request_start": {
      if (!e.patient_id) return state;
      const { patients, order } = ensurePatient(state, e.patient_id);
      const p = patients[e.patient_id];
      return {
        ...state,
        order,
        patients: {
          ...patients,
          [e.patient_id]: { ...p, status: "analyzing", vitals: e.vitals ?? p.vitals, updatedAt: e.ts },
        },
      };
    }
    case "placement": {
      if (!e.patient_id) return state;
      const { patients, order } = ensurePatient(state, e.patient_id);
      const p = patients[e.patient_id];
      return {
        ...state,
        order,
        patients: { ...patients, [e.patient_id]: { ...p, tier: e.device_id, status: "analyzing" } },
        activity: pushActivity(state, {
          id: `${e.type}-${e.task_id}-${e.ts}`,
          ts: e.ts,
          text: e.reason || `${e.patient_id} → ${e.device_id}`,
          tone: "info",
        }),
      };
    }
    case "failover": {
      return {
        ...state,
        activity: pushActivity(state, {
          id: `${e.type}-${e.task_id}-${e.ts}`,
          ts: e.ts,
          text: e.reason || `failover from ${e.from_device}`,
          tone: "warning",
        }),
      };
    }
    case "task_done": {
      const r = e.result || {};
      const pid = e.patient_id || r.patient_id;
      if (!pid) return state;
      const { patients, order } = ensurePatient(state, pid);
      const p = patients[pid];
      return {
        ...state,
        order,
        patients: {
          ...patients,
          [pid]: {
            ...p,
            severity: r.severity ?? p.severity,
            transcript: r.transcript ?? p.transcript,
            tier: e.device_id ?? p.tier,
            status: "idle",
            updatedAt: e.ts,
          },
        },
        activity: pushActivity(state, {
          id: `${e.type}-${e.task_id}-${e.ts}`,
          ts: e.ts,
          text: `${pid}: ${r.severity ?? "done"} via ${e.device_id}`,
          tone: r.severity === "emergency" ? "critical" : r.severity === "mild" ? "warning" : "success",
        }),
      };
    }
    case "sos": {
      const pid = e.patient_id;
      if (!pid) return state;
      const { patients, order } = ensurePatient(state, pid);
      const p = patients[pid];
      SEQ += 1;
      return {
        ...state,
        order,
        patients: {
          ...patients,
          [pid]: {
            ...p,
            severity: "emergency",
            emergencyReason: e.reason,
            vitals: e.vitals ?? p.vitals,
            updatedAt: e.ts,
          },
        },
        lastSos: { patient_id: pid, reason: e.reason || "Extreme vitals detected", ts: e.ts, seq: SEQ },
        activity: pushActivity(state, {
          id: `sos-${pid}-${e.ts}`,
          ts: e.ts,
          text: `🚨 EMERGENCY ${pid}: ${e.reason ?? ""} (${e.source ?? "watchdog"})`,
          tone: "critical",
        }),
      };
    }
    default:
      return state;
  }
}

/** Clear the emergency flag on a patient once the doctor acknowledges it. */
export function acknowledge(state: AppState, patientId: string): AppState {
  const p = state.patients[patientId];
  if (!p) return state;
  return {
    ...state,
    patients: { ...state.patients, [patientId]: { ...p, emergencyReason: undefined } },
  };
}
