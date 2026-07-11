export const NEURAROUTE_TOPICS = {
  heartbeat: "neuraroute/heartbeat",
  event: "neuraroute/event",
  admin: "neuraroute/admin",
  task: (deviceId: string) => `neuraroute/task/${deviceId}`,
  result: (taskId: string) => `neuraroute/result/${taskId}`,
} as const;

export type NeuraRouteDeviceId = string;

export type NeuraRouteAccelerator = "cpu" | "gpu" | "npu";

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

export type NeuraRoutePriority = "normal" | "high";

export interface NeuraRouteBatteryState {
  percent: number;
  charging: boolean;
}

export interface NeuraRouteHeartbeat {
  device_id: NeuraRouteDeviceId;
  ts: number;
  accelerators: NeuraRouteAccelerator[];
  models: string[];
  battery: NeuraRouteBatteryState | null;
  cpu_load?: number;
  npu_load?: number;
  temperature_c?: number;
  ram_free_mb?: number;
  net?: {
    reachable?: boolean;
    latency_ms?: number;
  };
  privacy_ok?: boolean;
  telemetry_mode?: "real" | "simulated";
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
  score?: Record<string, unknown>;
  heartbeat?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  priority?: NeuraRoutePriority;
}