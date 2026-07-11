"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardHeader } from "./dashboard-header";
import { DashboardShell } from "./dashboard-shell";
import { DeviceStateWindow } from "./device-state-window";
import { DecisionLog } from "./decision-log";
import { FailoverTheater } from "./failover-theater";
import { MetricsPanel } from "./metrics-panel";
import { PolicyToggle } from "./policy-toggle";
import { SummaryStrip } from "./summary-strip";
import { WorkflowDag } from "./workflow-dag";
import { TaskCreationWindow } from "./task-creation-window";
import { NEURAROUTE_TOPICS, type NeuraRouteEvent, type NeuraRouteHeartbeat } from "./contracts";
import type { DashboardSnapshot } from "./types";

interface DashboardPageProps {
  snapshot: DashboardSnapshot;
}

type StreamState = "connecting" | "connected" | "reconnecting" | "disconnected";

const deviceAliases: Record<string, string> = {
  "pc-01": "surface",
  "phone-01": "phone",
  "arduino-01": "unoq",
  "cloud-01": "cloud",
};

const taskNodeAliases: Record<string, string> = {
  t1: "t1",
  t2: "t2",
  t3: "t3",
  t4: "t4",
  t5: "t5",
};

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function DashboardPage({ snapshot }: DashboardPageProps) {
  const [liveSnapshot, setLiveSnapshot] = useState(snapshot);
  const [streamState, setStreamState] = useState<StreamState>("connecting");
  const [streamCopy, setStreamCopy] = useState("Connecting to the fake engine stream...");

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof window.setTimeout> | null = null;
    let reconnectAttempt = 0;
    let replayTimer: ReturnType<typeof window.setTimeout> | null = null;
    let replayTimers: Array<ReturnType<typeof window.setTimeout>> = [];
    let replayRunning = false;

    const wsUrl = process.env.NEXT_PUBLIC_NEURAROUTE_WS_URL ?? "ws://localhost:8000/ws";

    const clearReconnectTimer = () => {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const clearReplayTimers = () => {
      replayTimers.forEach((timer) => window.clearTimeout(timer));
      replayTimers = [];

      if (replayTimer !== null) {
        window.clearTimeout(replayTimer);
        replayTimer = null;
      }
    };

    const startReplay = () => {
      if (cancelled || replayRunning) {
        return;
      }

      replayRunning = true;
      setStreamState("connected");
      setStreamCopy("Fake engine unavailable locally, replaying the storyboard in-browser.");

      let elapsedMs = 0;
      fakeEngineStoryboard().forEach(([event, waitMs]) => {
        replayTimer = window.setTimeout(() => {
          if (!cancelled) {
            setLiveSnapshot((currentSnapshot) => applyEventToSnapshot(currentSnapshot, event));
          }
        }, elapsedMs);

        replayTimers.push(replayTimer);
        elapsedMs += waitMs;
      });

      const loopDelayMs = Math.max(elapsedMs, 2000);
      replayTimer = window.setTimeout(() => {
        if (!cancelled) {
          replayRunning = false;
          startReplay();
        }
      }, loopDelayMs);
      replayTimers.push(replayTimer);
    };

    const connect = () => {
      if (cancelled) {
        return;
      }

      clearReconnectTimer();
      setStreamState((currentState) => (currentState === "connected" ? currentState : reconnectAttempt === 0 ? "connecting" : "reconnecting"));
      setStreamCopy(reconnectAttempt === 0 ? `Connecting to ${wsUrl}` : `Reconnecting to ${wsUrl}...`);

      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        reconnectAttempt = 0;
        setStreamState("connected");
        setStreamCopy(`Streaming ${NEURAROUTE_TOPICS.event}`);
        clearReplayTimers();
        replayRunning = false;
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as NeuraRouteEvent;
          setLiveSnapshot((currentSnapshot) => applyEventToSnapshot(currentSnapshot, event));
        } catch {
          // Ignore malformed demo payloads.
        }
      };

      socket.onerror = () => {
        if (!cancelled) {
          setStreamState("reconnecting");
          setStreamCopy(`Stream error at ${wsUrl}; retrying...`);
        }
      };

      socket.onclose = () => {
        if (cancelled) {
          return;
        }

        if (!replayRunning) {
          clearReconnectTimer();
          startReplay();
          return;
        }

        setStreamState("reconnecting");
        setStreamCopy(`Stream closed at ${wsUrl}; retrying...`);

        const delayMs = Math.min(1000 * 2 ** reconnectAttempt, 8000);
        reconnectAttempt += 1;
        reconnectTimer = window.setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearReconnectTimer();
      clearReplayTimers();
      socket?.close();
    };
  }, []);

  const hasRunningTasks = useMemo(
    () => liveSnapshot.dagNodes.some((node) => node.status === "running"),
    [liveSnapshot.dagNodes],
  );

  return (
    <DashboardShell>
      <DashboardHeader
        title={liveSnapshot.headline}
        subtitle={liveSnapshot.subheadline}
      />

      <div className="mt-2 flex justify-end">
        <div
          className={`rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.22em] ${streamState === "connected"
            ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"
            : streamState === "reconnecting"
              ? "border-amber-400/20 bg-amber-400/10 text-amber-100"
              : "border-rose-400/20 bg-rose-400/10 text-rose-100"
            }`}
        >
          {streamCopy}
        </div>
      </div>

      <div className="space-y-4">
        <SummaryStrip items={liveSnapshot.summary} />
        <DeviceStateWindow devices={liveSnapshot.devices} />

        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.55fr)_minmax(340px,0.95fr)]">
          <div className="space-y-4">
            <WorkflowDag nodes={liveSnapshot.dagNodes} edges={liveSnapshot.dagEdges} />
          </div>

          <div className="space-y-4">
            <PolicyToggle mode={liveSnapshot.policyMode} />
            <FailoverTheater story={liveSnapshot.failoverStory} />
            <MetricsPanel metrics={liveSnapshot.metrics} />
            <DecisionLog entries={liveSnapshot.decisions} />
          </div>
        </div>
      </div>

      <TaskCreationWindow hasRunningTasks={hasRunningTasks} />
    </DashboardShell>
  );
}

function applyEventToSnapshot(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  switch (event.type) {
    case "device_alive":
      return applyDeviceAlive(snapshot, event);
    case "placement":
      return applyPlacement(snapshot, event);
    case "task_start":
      return applyTaskStart(snapshot, event);
    case "task_done":
      return applyTaskDone(snapshot, event);
    case "failover":
      return applyFailover(snapshot, event);
    case "metrics":
      return applyMetrics(snapshot, event);
    case "request_start":
      return appendDecision(snapshot, event, "info");
    case "request_done":
      return finishRequest(snapshot, event);
    case "device_stale":
      return markDeviceStale(snapshot, event);
    case "policy":
      return snapshot;
    case "sos":
      return snapshot;
    default:
      return snapshot;
  }
}

function applyDeviceAlive(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const deviceId = mapDeviceId(event.device_id);
  if (!deviceId) {
    return snapshot;
  }

  return {
    ...snapshot,
    devices: snapshot.devices.map((device) =>
      device.id !== deviceId ? device : updateDeviceFromHeartbeat(device, event.heartbeat),
    ),
  };
}

function applyPlacement(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const taskId = mapTaskNodeId(event.task_id);
  const deviceId = mapDeviceId(event.device_id);

  return {
    ...snapshot,
    dagNodes: updateDagNode(snapshot.dagNodes, taskId, {
      deviceId,
      status: "running",
    }),
    devices: updateDevice(snapshot.devices, deviceId, {
      status: "busy",
      activeTask: event.op,
    }),
    decisions: appendDecisionEntry(snapshot.decisions, {
      id: `${event.task_id ?? event.type}-${event.device_id ?? "unknown"}-placement`,
      timestamp: formatEventTime(event.ts),
      task: `${taskId ?? event.task_id ?? "task"} ${event.op ?? "placement"}`,
      device: deviceLabel(deviceId),
      reason: event.reason ?? "Placed by fake engine",
      tone: "info",
    }),
  };
}

function applyTaskStart(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const taskId = mapTaskNodeId(event.task_id);
  const deviceId = mapDeviceId(event.device_id);

  return {
    ...snapshot,
    dagNodes: updateDagNode(snapshot.dagNodes, taskId, {
      deviceId,
      status: "running",
    }),
    devices: updateDevice(snapshot.devices, deviceId, {
      status: "busy",
      activeTask: event.op,
    }),
  };
}

function applyTaskDone(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const taskId = mapTaskNodeId(event.task_id);
  const deviceId = mapDeviceId(event.device_id);

  return {
    ...snapshot,
    dagNodes: updateDagNode(snapshot.dagNodes, taskId, {
      deviceId,
      status: "complete",
    }),
    devices: updateDevice(snapshot.devices, deviceId, {
      status: "online",
      activeTask: undefined,
    }),
    decisions: appendDecisionEntry(snapshot.decisions, {
      id: `${event.task_id ?? event.type}-${event.device_id ?? "unknown"}-done`,
      timestamp: formatEventTime(event.ts),
      task: `${taskId ?? event.task_id ?? "task"} done`,
      device: deviceLabel(deviceId),
      reason: event.reason ?? "Task completed in fake engine",
      tone: "success",
    }),
  };
}

function applyFailover(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const taskId = mapTaskNodeId(event.task_id);
  const fromDeviceId = mapDeviceId(event.from_device);
  const deviceId = mapDeviceId(event.device_id);

  return {
    ...snapshot,
    failoverStory: {
      task: taskId ?? event.task_id ?? snapshot.failoverStory.task,
      fromDevice: deviceLabel(fromDeviceId),
      toDevice: deviceLabel(deviceId),
      reason: event.reason ?? snapshot.failoverStory.reason,
      status: "active",
    },
    devices: snapshot.devices.map((device) => {
      if (device.id === fromDeviceId) {
        return { ...device, status: "failover", activeTask: undefined };
      }

      if (device.id === deviceId) {
        return { ...device, status: "busy", activeTask: event.op ?? device.activeTask };
      }

      return device;
    }),
    decisions: appendDecisionEntry(snapshot.decisions, {
      id: `${event.task_id ?? event.type}-${event.device_id ?? "unknown"}-failover`,
      timestamp: formatEventTime(event.ts),
      task: `${taskId ?? event.task_id ?? "task"} failover`,
      device: deviceLabel(deviceId),
      reason: event.reason ?? "Task migrated after heartbeat loss",
      tone: "warning",
    }),
  };
}

function applyMetrics(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const metrics = event.metrics;
  if (!metrics || typeof metrics !== "object") {
    return snapshot;
  }

  return {
    ...snapshot,
    metrics: [
      {
        label: "End-to-end latency",
        value: formatMetric(metrics, "latency_orchestrated_s", "latency_orchestrated", "latency", "6.4 s"),
        detail: "Orchestrated run from the fake engine stream.",
      },
      {
        label: "Cloud calls",
        value: formatMetric(metrics, "cloud_calls", "cloudCalls", "2"),
        detail: "Cloud fallback count captured from the stream.",
      },
      {
        label: "Battery delta",
        value: `${formatMetric(metrics, "battery_delta_pct", "batteryDelta", "3.0")}%`,
        detail: "Observed change across the demo sequence.",
      },
      {
        label: "Failover time",
        value: `${formatMetric(metrics, "failover_time_s", "failoverTime", "1.8")} s`,
        detail: "Live reroute timing from the fake engine.",
      },
    ],
  };
}

function finishRequest(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  return {
    ...snapshot,
    failoverStory: event.reason
      ? { ...snapshot.failoverStory, reason: event.reason, status: "resolved" }
      : { ...snapshot.failoverStory, status: "resolved" },
  };
}

function markDeviceStale(snapshot: DashboardSnapshot, event: NeuraRouteEvent): DashboardSnapshot {
  const deviceId = mapDeviceId(event.device_id);
  return {
    ...snapshot,
    devices: updateDevice(snapshot.devices, deviceId, { status: "failover" }),
  };
}

function appendDecision(snapshot: DashboardSnapshot, event: NeuraRouteEvent, tone: DashboardSnapshot["decisions"][number]["tone"]): DashboardSnapshot {
  return {
    ...snapshot,
    decisions: appendDecisionEntry(snapshot.decisions, {
      id: `${event.type}-${event.ts}`,
      timestamp: formatEventTime(event.ts),
      task: event.task_id ?? event.request_id ?? event.type,
      device: deviceLabel(mapDeviceId(event.device_id)),
      reason: event.reason ?? "Request started in fake engine",
      tone,
    }),
  };
}

function updateDeviceFromHeartbeat(device: DashboardSnapshot["devices"][number], heartbeat: NeuraRouteEvent["heartbeat"]): DashboardSnapshot["devices"][number] {
  if (!heartbeat || typeof heartbeat !== "object") {
    return { ...device, status: "online" };
  }

  const heartbeatData = heartbeat as NeuraRouteHeartbeat;
  return {
    ...device,
    status: "online",
    battery: heartbeatData.battery?.percent ?? device.battery,
    cpuLoad: heartbeatData.cpu_load !== undefined ? Math.round(heartbeatData.cpu_load * 100) : device.cpuLoad,
    npuLoad: heartbeatData.npu_load !== undefined ? Math.round(heartbeatData.npu_load * 100) : device.npuLoad,
  };
}

function updateDevice(devices: DashboardSnapshot["devices"], deviceId: string | undefined, updates: Partial<DashboardSnapshot["devices"][number]>): DashboardSnapshot["devices"] {
  if (!deviceId) {
    return devices;
  }

  return devices.map((device) => (device.id === deviceId ? { ...device, ...updates } : device));
}

function updateDagNode(nodes: DashboardSnapshot["dagNodes"], taskId: string | undefined, updates: Partial<DashboardSnapshot["dagNodes"][number]>): DashboardSnapshot["dagNodes"] {
  if (!taskId) {
    return nodes;
  }

  return nodes.map((node) => (node.id === taskId ? { ...node, ...updates } : node));
}

function appendDecisionEntry(entries: DashboardSnapshot["decisions"], entry: DashboardSnapshot["decisions"][number]): DashboardSnapshot["decisions"] {
  return [...entries, entry].slice(-6);
}

function mapDeviceId(deviceId: string | undefined): string | undefined {
  if (!deviceId) {
    return undefined;
  }

  return deviceAliases[deviceId] ?? deviceId;
}

function mapTaskNodeId(taskId: string | undefined): string | undefined {
  if (!taskId) {
    return undefined;
  }

  const candidate = taskId.slice(taskId.lastIndexOf("-") + 1);
  return taskNodeAliases[candidate] ?? candidate;
}

function deviceLabel(deviceId: string | undefined): string {
  switch (deviceId) {
    case "surface":
      return "Surface Laptop 7";
    case "phone":
      return "OnePlus 15";
    case "unoq":
      return "Arduino UNO Q";
    case "cloud":
      return "Qualcomm AI Cloud 100";
    default:
      return "unassigned";
  }
}

function formatEventTime(ts: number): string {
  return dateTimeFormatter.format(new Date(ts * 1000));
}

function formatMetric(metrics: Record<string, unknown>, primaryKey: string, secondaryKey: string, tertiaryKey?: string, fallback = "0"): string {
  const rawValue = metrics[primaryKey] ?? metrics[secondaryKey] ?? (tertiaryKey ? metrics[tertiaryKey] : undefined);
  if (typeof rawValue === "number") {
    return String(rawValue);
  }

  if (typeof rawValue === "string") {
    return rawValue;
  }

  return fallback;
}

function fakeEngineStoryboard(): Array<[NeuraRouteEvent, number]> {
  const requestId = "req-demo";

  return [
    [
      {
        type: "device_alive",
        ts: nowSeconds(),
        device_id: "pc-01",
        reason: "pc-01 joined (cpu,npu)",
        heartbeat: {
          accelerators: ["cpu", "npu"],
          privacy_ok: true,
          battery: null,
          cpu_load: 0.32,
          npu_load: 0.1,
        },
      },
      400,
    ],
    [
      {
        type: "device_alive",
        ts: nowSeconds() + 1,
        device_id: "phone-01",
        reason: "phone-01 joined (cpu,npu)",
        heartbeat: {
          accelerators: ["cpu", "npu"],
          privacy_ok: true,
          battery: { percent: 78, charging: false },
          cpu_load: 0.24,
          npu_load: 0.18,
        },
      },
      400,
    ],
    [
      {
        type: "device_alive",
        ts: nowSeconds() + 2,
        device_id: "arduino-01",
        reason: "arduino-01 joined (cpu)",
        heartbeat: {
          accelerators: ["cpu"],
          privacy_ok: true,
          battery: null,
          cpu_load: 0.19,
          npu_load: 0.08,
        },
      },
      400,
    ],
    [
      {
        type: "device_alive",
        ts: nowSeconds() + 3,
        device_id: "cloud-01",
        reason: "cloud-01 joined (cpu,gpu)",
        heartbeat: {
          accelerators: ["cpu", "gpu"],
          privacy_ok: false,
          battery: null,
          cpu_load: 0.12,
          npu_load: 0,
        },
      },
      400,
    ],
    [
      {
        type: "request_start",
        ts: nowSeconds() + 4,
        request_id: requestId,
        reason: "health-report.pdf uploaded from phone -> 5-task DAG",
      },
      600,
    ],
    [
      {
        type: "placement",
        ts: nowSeconds() + 5,
        request_id: requestId,
        task_id: `${requestId}-t1`,
        op: "extract_text",
        device_id: "pc-01",
        reason: "pc-01: PyMuPDF, NPU free, on-device (sensitive)",
      },
      200,
    ],
    [
      {
        type: "task_start",
        ts: nowSeconds() + 6,
        request_id: requestId,
        task_id: `${requestId}-t1`,
        op: "extract_text",
        device_id: "pc-01",
      },
      900,
    ],
    [
      {
        type: "task_done",
        ts: nowSeconds() + 7,
        request_id: requestId,
        task_id: `${requestId}-t1`,
        op: "extract_text",
        device_id: "pc-01",
        reason: "extracted 1,240 words",
      },
      300,
    ],
    [
      {
        type: "placement",
        ts: nowSeconds() + 8,
        request_id: requestId,
        task_id: `${requestId}-t2`,
        op: "summarize",
        device_id: "phone-01",
        reason: "phone-01: on-device (sensitive), NPU free, lowest energy",
        score: { latency: 0.4, energy: 0.2, cost: 0, privacy: 1, total: 0.31 },
      },
      150,
    ],
    [
      {
        type: "placement",
        ts: nowSeconds() + 9,
        request_id: requestId,
        task_id: `${requestId}-t3`,
        op: "flag_risk",
        device_id: "pc-01",
        reason: "pc-01: parallel with t2 on a DIFFERENT device, NPU headroom",
        score: { latency: 0.3, energy: 0.3, cost: 0, privacy: 1, total: 0.29 },
      },
      300,
    ],
    [
      {
        type: "task_start",
        ts: nowSeconds() + 10,
        request_id: requestId,
        task_id: `${requestId}-t2`,
        op: "summarize",
        device_id: "phone-01",
      },
      100,
    ],
    [
      {
        type: "task_start",
        ts: nowSeconds() + 11,
        request_id: requestId,
        task_id: `${requestId}-t3`,
        op: "flag_risk",
        device_id: "pc-01",
      },
      1000,
    ],
    [
      {
        type: "failover",
        ts: nowSeconds() + 12,
        request_id: requestId,
        task_id: `${requestId}-t2`,
        op: "summarize",
        from_device: "phone-01",
        device_id: "cloud-01",
        reason: "phone-01 missed heartbeat (>3s) -> re-route t2 to cloud-01",
      },
      400,
    ],
    [
      {
        type: "task_done",
        ts: nowSeconds() + 13,
        request_id: requestId,
        task_id: `${requestId}-t3`,
        op: "flag_risk",
        device_id: "pc-01",
        reason: "risk: LOW",
      },
      300,
    ],
    [
      {
        type: "task_start",
        ts: nowSeconds() + 14,
        request_id: requestId,
        task_id: `${requestId}-t2`,
        op: "summarize",
        device_id: "cloud-01",
      },
      1200,
    ],
    [
      {
        type: "task_done",
        ts: nowSeconds() + 15,
        request_id: requestId,
        task_id: `${requestId}-t2`,
        op: "summarize",
        device_id: "cloud-01",
        reason: "summary ready (recovered)",
      },
      300,
    ],
    [
      {
        type: "placement",
        ts: nowSeconds() + 16,
        request_id: requestId,
        task_id: `${requestId}-t5`,
        op: "population_stats",
        device_id: "cloud-01",
        reason: "cloud-01: public data, cloud-eligible, aggregate stats",
      },
      200,
    ],
    [
      {
        type: "task_start",
        ts: nowSeconds() + 17,
        request_id: requestId,
        task_id: `${requestId}-t5`,
        op: "population_stats",
        device_id: "cloud-01",
      },
      800,
    ],
    [
      {
        type: "task_done",
        ts: nowSeconds() + 18,
        request_id: requestId,
        task_id: `${requestId}-t5`,
        op: "population_stats",
        device_id: "cloud-01",
      },
      200,
    ],
    [
      {
        type: "placement",
        ts: nowSeconds() + 19,
        request_id: requestId,
        task_id: `${requestId}-t4`,
        op: "patient_explainer",
        device_id: "pc-01",
        reason: "pc-01: needs t2 & t3, on-device (sensitive)",
      },
      200,
    ],
    [
      {
        type: "task_start",
        ts: nowSeconds() + 20,
        request_id: requestId,
        task_id: `${requestId}-t4`,
        op: "patient_explainer",
        device_id: "pc-01",
      },
      900,
    ],
    [
      {
        type: "task_done",
        ts: nowSeconds() + 21,
        request_id: requestId,
        task_id: `${requestId}-t4`,
        op: "patient_explainer",
        device_id: "pc-01",
      },
      300,
    ],
    [
      {
        type: "metrics",
        ts: nowSeconds() + 22,
        request_id: requestId,
        metrics: {
          latency_orchestrated_s: 6.4,
          latency_baseline_s: 19.8,
          speedup: 3.1,
          cloud_calls: 2,
          battery_delta_pct: 3.0,
          failover_time_s: 1.8,
        },
      },
      400,
    ],
    [
      {
        type: "request_done",
        ts: nowSeconds() + 23,
        request_id: requestId,
        reason: "run complete",
      },
      2500,
    ],
  ];
}

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}