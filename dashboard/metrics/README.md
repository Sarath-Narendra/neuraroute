# metrics/ — Benchmark (owner: Eswar)

`run_bench.py` runs the same request twice — **baseline** (force everything onto one device,
sequential) vs **orchestrated** — and emits `metrics.json`:

- end-to-end latency
- number of cloud calls
- battery delta
- failover time

These are the **real, measured** numbers the demo's "numbers" beat depends on (40-pt Technical
Implementation criterion) — not illustrative figures. Target: stable within ±20% across 3 runs.

`metrics.json` is committed (it's a deliverable the dashboard reads).
