# NeuraRoute — 5-minute demo script (v1 draft)

**Presenter:** Sarath. **Drives PC/upload:** Eswar. **Points at dashboard:** Abhiram. **Performs THE KILL:** Gowtham.
**Rehearse to finish at 4:30** — the 30 s buffer is the plan, not luck. Every claim below is something the system
*actually does* (reasons are the scheduler's real output; numbers are measured, not asserted). No diagnosis claims.

> **Before you start (idle "attract" screen):** dashboard shows **4 green tiles** — Surface, OnePlus, Uno Q, AI Cloud 100 —
> heartbeats ticking. Broker up, `demo_reset.sh` already run, backup video cued on a second phone.

---

### 0:00–0:45 · Problem
> "Every AI app today makes one silent assumption: that it knows **where** the AI runs. On the cloud. Or on the phone.
> Hard-coded, forever. But reality moves — **batteries drain, networks drop, and some data must never leave your hand.**
> For an ASHA health worker in a rural clinic on one bar of signal, that assumption breaks the moment it matters most."

*Stage: you speak over the idle 4-tile screen. Calm. Let the tiles tick.*

### 0:45–1:15 · What NeuraRoute is (the one-liner)
> "NeuraRoute is an orchestration layer that decides, **at runtime, which device runs each AI task** — and re-routes
> live when conditions change. Four Snapdragon devices behaving as **one cooperative AI computer.**"

*Stage: point across the 4 tiles — Surface, OnePlus, Uno Q, AI Cloud 100.*

### 1:15–2:45 · Live run (the heart)
> "Let's run a real health-report workflow. Eswar uploads a PDF **from the phone.**"

*Eswar uploads on the OnePlus. The DAG animates. You narrate the reasons **as they appear on screen** — they're the engine's, not yours:*

> "Text extraction lands on the Surface. Now watch — **summarize and risk-flagging run in parallel, on two different
> devices.** And notice: every sensitive task stays **on-device**. The only thing that reaches the cloud is the
> **non-sensitive** population statistic — because privacy here isn't a setting, it's a **hard constraint in the scheduler.**"

*Abhiram points at the two parallel nodes and the on-screen reason strings. Keep it to the DAG — don't over-explain.*

### 2:45–3:30 · THE KILL (the moment)
> "But what happens when reality hits?"

*Gowtham kills a device mid-run (physical unplug if 5/5 reliable, else `simulate_battery_critical`).*

> "A device just dropped. Missed heartbeat. Watch the tile go red — and the task **migrate live** to another device,
> with the reason on screen. The run **completes anyway.**"

*Let 3 seconds of silence land after it recovers. This is the beat that wins the multi-device prize.*
> "That's the failover time, right there on the panel."

### 3:30–4:15 · Numbers
> "And this is the part judges asked us to prove. Orchestrated versus a single-device baseline, **measured this
> morning on this hardware, not simulated:** end-to-end latency, cloud calls avoided, battery spared, and failover time."

*Metrics panel on screen — the engine emits `latency_s`, `cloud_calls`, `failovers`, `failover_time_s`; Eswar's bench adds the baseline column. Speak the rubric's own words: resource utilization, latency, energy efficiency.*

### 4:15–4:45 · Close
*If green, flip the policy live:*
> "One more thing — I'll switch our policy from speed-first to **battery-saver**… and watch the routing **change**,
> live. Same request, different priorities."

*Placement visibly shifts. Then land it:*
> "Kubernetes orchestrated the cloud. **NeuraRoute orchestrates the Ecosystem of You.** Every device you own,
> one adaptive AI computer — and it never breaks, because it re-routes around failure. Thank you."

---

## Q&A cheat sheet (§7b — everyone can answer their component)
- **"Why not just use the cloud?"** → privacy hard-constraint + latency + cost. *Show the cost function.*
- **"What's novel vs Kubernetes?"** → device heterogeneity, and battery/thermal/privacy/NPU as **live scheduling
  constraints on real consumer silicon**, with sub-second failover on lossy networks. A cloud scheduler can't claim this.
- **"Does it scale?"** → stateless scheduler; any MQTT-reachable device joins by heartbeat. Roadmap: a learned policy.
- **"Is the healthcare claim real?"** → we orchestrate a health *document* workflow. **No diagnosis claims** — the
  impact story is **access**, not medicine.

## Truth guardrails (do not overclaim)
- The **reasons** on screen are the scheduler's real output — read them, don't embellish.
- The **numbers** are measured live (Eswar's `run_bench.py` → `metrics.json`), not the PDF's illustrative figures.
- "Sensitive stays on-device" is enforced by the feasibility filter — it's a fact, say it plainly.
