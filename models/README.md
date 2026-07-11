# models/ — Model Ops & Cloud (owner: Eswar)

One op behind one signature everyone calls: **`run_model("triage", payload) -> result`**,
where `payload = {patient_id, vitals, profile}` and the result carries
`{patient_id, severity, transcript}`. Models are black boxes — zero weight tuning; the work
is prompt engineering.

| Piece | Role |
|---|---|
| `ops.py` | `triage` — cross-reference a reading against the patient record via the local LLM |
| `tripwire.py` | hard numeric safety floor (HR/SpO₂/temp/resp bounds) — the watchdog's failsafe |
| `registry.py` | which model + adapter runs `triage` per tier. `NEURAROUTE_REGISTRY=dev` (all local/mock) or `venue` (real `/infer` servers). `type` picks the path: `infer_http` / `cloud` / local |
| `infer_client.py` | bridge to the standalone inference module — `POST /infer`, maps its schema → `{severity, transcript}` (venue mode) |
| `llm_client.py` | OpenAI-compatible client for local tiers (LM Studio / llama.cpp) |
| `cloud_adapter.py` | canned GPT mock for `dev` mode; **mock on** by default so demos never hang |

Dev: point local tiers at any OpenAI-compatible server via `NEURAROUTE_LOCAL_BASE_URL` (or
`tools/mock_llm.py`). Venue: `NEURAROUTE_REGISTRY=venue` + `NEURAROUTE_INFER_LAPTOP_URL`/
`NEURAROUTE_INFER_CLOUD_URL` point at the real `/infer` servers. Weights are gitignored.
