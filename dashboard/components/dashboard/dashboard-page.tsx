import { ConnectionBanner } from "./connection-banner";
import { DashboardHeader } from "./dashboard-header";
import { DashboardShell } from "./dashboard-shell";
import { DecisionLog } from "./decision-log";
import { DeviceGrid } from "./device-grid";
import { FailoverTheater } from "./failover-theater";
import { MetricsPanel } from "./metrics-panel";
import { PolicyToggle } from "./policy-toggle";
import { SummaryStrip } from "./summary-strip";
import { WorkflowDag } from "./workflow-dag";
import type { DashboardSnapshot } from "./types";

interface DashboardPageProps {
  snapshot: DashboardSnapshot;
}

export function DashboardPage({ snapshot }: DashboardPageProps) {
  return (
    <DashboardShell>
      <DashboardHeader
        title={snapshot.headline}
        subtitle={snapshot.subheadline}
        connectionState={snapshot.connectionState}
        connectionCopy={snapshot.connectionCopy}
      />

      <ConnectionBanner state={snapshot.connectionState} message={snapshot.connectionCopy} />

      <div className="space-y-4">
        <SummaryStrip items={snapshot.summary} />

        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.55fr)_minmax(340px,0.95fr)]">
          <div className="space-y-4">
            <WorkflowDag nodes={snapshot.dagNodes} edges={snapshot.dagEdges} />
            <DeviceGrid devices={snapshot.devices} />
          </div>

          <div className="space-y-4">
            <PolicyToggle mode={snapshot.policyMode} />
            <FailoverTheater story={snapshot.failoverStory} />
            <MetricsPanel metrics={snapshot.metrics} />
            <DecisionLog entries={snapshot.decisions} />
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}