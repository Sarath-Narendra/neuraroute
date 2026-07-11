export type DeviceStatus = "online" | "busy" | "failover" | "offline";

export type PolicyMode = "speed-first" | "battery-saver" | "privacy-first";

export interface DashboardDevice {
  id: string;
  name: string;
  kind: string;
  status: DeviceStatus;
  battery: number;
  cpuLoad: number;
  npuLoad: number;
  activeTask?: string;
}

export interface DagNode {
  id: string;
  label: string;
  deviceId?: string;
  status: "pending" | "running" | "complete" | "failed";
}

export interface DagEdge {
  from: string;
  to: string;
  label?: string;
}

export interface DecisionLogEntry {
  id: string;
  timestamp: string;
  task: string;
  device: string;
  reason: string;
  tone: "info" | "success" | "warning" | "critical";
}

export interface MetricItem {
  label: string;
  value: string;
  detail: string;
}

export interface FailoverStory {
  task: string;
  fromDevice: string;
  toDevice: string;
  reason: string;
  status: "ready" | "active" | "resolved";
}

export interface DashboardSnapshot {
  headline: string;
  subheadline: string;
  summary: MetricItem[];
  devices: DashboardDevice[];
  dagNodes: DagNode[];
  dagEdges: DagEdge[];
  decisions: DecisionLogEntry[];
  metrics: MetricItem[];
  policyMode: PolicyMode;
  failoverStory: FailoverStory;
}