"""Orchestrator v2: run one reading's triage task down the connectivity ladder.

Lifecycle of a run (= one vitals reading):
  plan (single triage task) -> dispatch to the highest alive tier -> collect the
  verdict -> emit task_done (with the triage result) + metrics + request_done.

Failover paths (all re-route through the SAME ladder, excluding the failed tier):
  * tier drops        — ResourceGraph marks it stale (>3 s) -> on_device_stale re-schedules
  * tier errors       — result arrives with status error (e.g. GPT call failed: no
                        internet) -> on_result re-schedules. THIS is "internet down ->
                        slide down the ladder" in practice.
  * task times out    — per-task deadline elapses with no result -> _check_timeout

All methods run on the asyncio loop. Results arrive on the paho thread, so app.py
marshals on_result / on_device_stale onto the loop via call_soon_threadsafe.
"""
import json
import logging
import time

from contracts.topics import (
    EV_FAILOVER, EV_METRICS, EV_PLACEMENT, EV_REQUEST_DONE, EV_REQUEST_START,
    EV_TASK_DONE, EV_TASK_START, PRIORITY_LADDER, TIER_LABELS, topic_task,
)
from engine.planner import plan_request

log = logging.getLogger("engine.orch")

RETRY_DELAY_S = 1.5      # when no tier is feasible yet, retry shortly
MAX_RETRIES = 6


class Run:
    def __init__(self, request_id, tasks, patient_id=None, vitals=None, profile=None):
        self.request_id = request_id
        self.patient_id = patient_id
        self.vitals = vitals or {}
        self.profile = profile or {}
        self.tasks = {}
        for t in tasks:
            t.update(status="pending", assigned=None, result=None,
                     dispatched_at=None, excluded=set(), timeout=None, retries=0)
            self.tasks[t["task_id"]] = t
        self.started = time.time()
        self.cloud_calls = 0
        self.failovers = 0
        self.failover_time_s = None

    def all_done(self):
        return all(t["status"] == "done" for t in self.tasks.values())


class Orchestrator:
    def __init__(self, graph, scheduler, publish, emit, loop):
        self.graph = graph
        self.scheduler = scheduler
        self.publish = publish            # (topic:str, payload:str) -> None  (paho, thread-safe)
        self.emit = emit                  # (event:dict) -> None
        self.loop = loop
        self.runs = {}

    # --- start ---
    def start_run(self, request_id, patient_id=None, vitals=None, profile=None):
        run = Run(request_id, plan_request(request_id),
                  patient_id=patient_id, vitals=vitals, profile=profile)
        self.runs[request_id] = run
        vit = ", ".join(f"{k}={v}" for k, v in (vitals or {}).items())
        log.info("run %s started (patient=%s, %s)", request_id, patient_id, vit)
        self.emit({"type": EV_REQUEST_START, "ts": time.time(), "request_id": request_id,
                   "patient_id": patient_id, "vitals": vitals or {},
                   "reason": f"reading for {patient_id}: {vit}"})
        self._dispatch_ready(run)
        return run

    # --- scheduling ---
    def _ready(self, run):
        return [t for t in run.tasks.values()
                if t["status"] == "pending"
                and all(run.tasks[d]["status"] == "done" for d in t["depends_on"])]

    def _busy_devices(self, run):
        return {t["assigned"] for t in run.tasks.values()
                if t["status"] == "dispatched" and t["assigned"]}

    def _dispatch_ready(self, run):
        busy = self._busy_devices(run)
        for t in self._ready(run):
            if self._dispatch_one(run, t, busy):
                busy.add(t["assigned"])

    def _build_payload(self, run, task):
        """What the tier receives: the reading + this patient's record. Devices with
        their own local records (arduino) may substitute their local copy."""
        return {"patient_id": run.patient_id, "vitals": run.vitals, "profile": run.profile}

    def _dispatch_one(self, run, task, busy):
        choice = self.scheduler.choose_device(task, exclude=task["excluded"], busy=busy)
        if not choice:
            task["retries"] += 1
            if task["retries"] > MAX_RETRIES:
                log.error("run %s: no tier for %s after %d retries — giving up",
                          run.request_id, task["task_id"], task["retries"])
                self.emit({"type": EV_FAILOVER, "ts": time.time(), "request_id": run.request_id,
                           "task_id": task["task_id"], "op": task["op"],
                           "patient_id": run.patient_id,
                           "reason": "every tier is down or has failed — run stalled"})
                return False
            self.loop.call_later(RETRY_DELAY_S, self._dispatch_ready, run)
            return False

        device_id, tier_idx, bd, reason = choice
        task["assigned"] = device_id
        task["status"] = "dispatched"
        task["dispatched_at"] = time.time()
        if device_id == PRIORITY_LADDER[0]:
            run.cloud_calls += 1

        msg = {
            "task_id": task["task_id"], "request_id": run.request_id, "op": task["op"],
            "payload": self._build_payload(run, task), "depends_on": task["depends_on"],
            "deadline_ms": task["deadline_ms"], "privacy": task["privacy"],
            "priority": task["priority"], "assigned_device": device_id,
        }
        self.publish(topic_task(device_id), json.dumps(msg))
        log.info("dispatch %s -> %s (tier %s)", task["task_id"], device_id, bd.get("tier"))
        self.emit({"type": EV_PLACEMENT, "ts": time.time(), "request_id": run.request_id,
                   "task_id": task["task_id"], "op": task["op"], "device_id": device_id,
                   "patient_id": run.patient_id, "reason": reason, "score": bd})
        self.emit({"type": EV_TASK_START, "ts": time.time(), "request_id": run.request_id,
                   "task_id": task["task_id"], "op": task["op"], "device_id": device_id,
                   "patient_id": run.patient_id})
        task["timeout"] = self.loop.call_later(
            task["deadline_ms"] / 1000.0, self._check_timeout, run.request_id, task["task_id"], device_id)
        return True

    # --- results ---
    def on_result(self, result):
        run = self.runs.get(result.get("request_id"))
        if not run:
            return
        task = run.tasks.get(result.get("task_id"))
        if not task or task["status"] != "dispatched":
            return                                   # duplicate / already re-routed away
        if result.get("device_id") != task["assigned"]:
            return                                   # stale result from a tier we moved off

        if result.get("status") != "ok":
            # THE LADDER: the tier answered but could not run the model (e.g. the cloud
            # tier's GPT call failed because the internet is down) -> next tier.
            err = result.get("error") or result.get("status")
            self._failover(run, task, task["assigned"],
                           f"{TIER_LABELS.get(task['assigned'], task['assigned'])} failed: {err}")
            return

        if task["timeout"]:
            task["timeout"].cancel()
            task["timeout"] = None
        task["status"] = "done"
        task["result"] = result.get("result")
        verdict = task["result"] if isinstance(task["result"], dict) else {}
        log.info("done %s on %s: %s (%.0f ms)", task["task_id"], result.get("device_id"),
                 verdict.get("severity", "?"), result.get("latency_ms") or 0)
        self.emit({"type": EV_TASK_DONE, "ts": time.time(), "request_id": run.request_id,
                   "task_id": task["task_id"], "op": task["op"],
                   "device_id": result.get("device_id"), "patient_id": run.patient_id,
                   "result": verdict,
                   "reason": f"{verdict.get('severity', 'done')} — via {TIER_LABELS.get(result.get('device_id'), result.get('device_id'))}"})
        if run.all_done():
            self._finish(run)
        else:
            self._dispatch_ready(run)

    # --- failover ---
    def _check_timeout(self, request_id, task_id, device_id):
        run = self.runs.get(request_id)
        task = run and run.tasks.get(task_id)
        if not task or task["status"] != "dispatched" or task["assigned"] != device_id:
            return
        self._failover(run, task, device_id, f"{task_id} deadline exceeded on {device_id}")

    def on_device_stale(self, device_id):
        for run in list(self.runs.values()):
            for task in list(run.tasks.values()):
                if task["status"] == "dispatched" and task["assigned"] == device_id:
                    self._failover(run, task, device_id, f"{device_id} dropped (missed heartbeat >3s)")

    def _failover(self, run, task, failed_device, reason):
        if task["status"] != "dispatched" or task["assigned"] != failed_device:
            return                                   # already handled
        if task["timeout"]:
            task["timeout"].cancel()
            task["timeout"] = None
        run.failovers += 1
        if run.failover_time_s is None and task["dispatched_at"]:
            run.failover_time_s = round(time.time() - task["dispatched_at"], 2)
        task["excluded"].add(failed_device)
        task["status"] = "pending"
        task["assigned"] = None
        log.warning("FAILOVER %s off %s: %s", task["task_id"], failed_device, reason)
        self.emit({"type": EV_FAILOVER, "ts": time.time(), "request_id": run.request_id,
                   "task_id": task["task_id"], "op": task["op"], "from_device": failed_device,
                   "patient_id": run.patient_id, "reason": reason})
        self._dispatch_one(run, task, self._busy_devices(run))

    # --- finish ---
    def _finish(self, run):
        latency = round(time.time() - run.started, 2)
        t1 = next(iter(run.tasks.values()))
        tier = t1["assigned"]
        verdict = t1["result"] if isinstance(t1["result"], dict) else {}
        metrics = {"latency_orchestrated_s": latency, "tier": tier,
                   "cloud_calls": run.cloud_calls, "failovers": run.failovers,
                   "failover_time_s": run.failover_time_s}
        log.info("run %s DONE in %.2fs  tier=%s severity=%s  metrics=%s",
                 run.request_id, latency, tier, verdict.get("severity"), metrics)
        self.emit({"type": EV_METRICS, "ts": time.time(), "request_id": run.request_id,
                   "patient_id": run.patient_id, "metrics": metrics})
        self.emit({"type": EV_REQUEST_DONE, "ts": time.time(), "request_id": run.request_id,
                   "patient_id": run.patient_id, "device_id": tier,
                   "severity": verdict.get("severity"),
                   "reason": f"triage complete in {latency:.1f}s via {TIER_LABELS.get(tier, tier)}"})

    def status(self):
        return {rid: {tid: {"status": t["status"], "device": t["assigned"]}
                      for tid, t in run.tasks.items()} for rid, run in self.runs.items()}
