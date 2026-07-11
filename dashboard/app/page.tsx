import { DashboardPage } from "@/components/dashboard";
import type { DashboardSnapshot } from "@/components/dashboard";

export default function Home() {
  const snapshot: DashboardSnapshot = {
    headline: "Neura Route",
    subheadline: "Simple dashboard for routing, failover, metrics, and policy control.",
    summary: [
      { label: "Devices online", value: "4", detail: "Surface, phone, Uno Q, and cloud" },
      { label: "Tasks in flight", value: "5", detail: "Parallel branches visible in the DAG" },
      { label: "Failovers today", value: "1", detail: "Structured for live reroute replay" },
      { label: "Median route time", value: "1.8 s", detail: "Placeholder until metrics are wired" },
    ],
    devices: [
      {
        id: "surface",
        name: "Surface Laptop 7",
        kind: "Primary compute",
        status: "busy",
        battery: 76,
        cpuLoad: 52,
        npuLoad: 41,
        activeTask: "summarize",
      },
      {
        id: "phone",
        name: "OnePlus 15",
        kind: "Mobile edge node",
        status: "online",
        battery: 68,
        cpuLoad: 24,
        npuLoad: 18,
        activeTask: "patient_explainer",
      },
      {
        id: "unoq",
        name: "Arduino UNO Q",
        kind: "Embedded node",
        status: "online",
        battery: 92,
        cpuLoad: 19,
        npuLoad: 8,
        activeTask: "doc_event_detect",
      },
      {
        id: "cloud",
        name: "Qualcomm AI Cloud 100",
        kind: "Cloud fallback",
        status: "failover",
        battery: 100,
        cpuLoad: 12,
        npuLoad: 0,
        activeTask: "population_stats",
      },
    ],
    dagNodes: [
      { id: "t1", label: "extract_text", deviceId: "surface", status: "complete" },
      { id: "t2", label: "summarize", deviceId: "surface", status: "running" },
      { id: "t3", label: "flag_risk", deviceId: "phone", status: "running" },
      { id: "t4", label: "patient_explainer", deviceId: "phone", status: "pending" },
      { id: "t5", label: "population_stats", deviceId: "cloud", status: "pending" },
    ],
    dagEdges: [
      { from: "t1", to: "t2" },
      { from: "t1", to: "t3" },
      { from: "t2", to: "t4", label: "sensitive path" },
      { from: "t3", to: "t5", label: "cloud-eligible" },
    ],
    decisions: [
      {
        id: "d1",
        timestamp: "09:14:02",
        task: "t2 summarize",
        device: "Surface Laptop 7",
        reason: "Highest local throughput with enough battery headroom for the current policy.",
        tone: "success",
      },
      {
        id: "d2",
        timestamp: "09:14:03",
        task: "t3 flag_risk",
        device: "OnePlus 15",
        reason: "Keeps the privacy-sensitive branch on an edge device while balancing load.",
        tone: "info",
      },
      {
        id: "d3",
        timestamp: "09:14:07",
        task: "t5 population_stats",
        device: "Qualcomm AI Cloud 100",
        reason: "Non-sensitive task was moved to cloud to preserve local battery and unlock parallelism.",
        tone: "warning",
      },
    ],
    metrics: [
      { label: "End-to-end latency", value: "1.8 s", detail: "Scaffolded for baseline vs orchestrated comparison." },
      { label: "Cloud calls", value: "1", detail: "Only the non-sensitive branch is eligible here." },
      { label: "Battery delta", value: "-6%", detail: "Reserved for the metrics panel and final benchmark." },
      { label: "Failover time", value: "<2 s", detail: "Placeholder target for the live migration story." },
    ],
    policyMode: "speed-first",
    failoverStory: {
      task: "t3 flag_risk",
      fromDevice: "Surface Laptop 7",
      toDevice: "OnePlus 15",
      reason:
        "The primary node was demoted mid-run, so the task moved to the next feasible edge device with a fresh heartbeat.",
      status: "active",
    },
  };

  return (
    <DashboardPage snapshot={snapshot} />
  );
}
