# models/ — Model Ops & Cloud (owner: Eswar)

One op behind one signature everyone calls: **`run_model("triage", payload) -> result`**,
where `payload = {patient_id, vitals, profile}` and the result carries
`{patient_id, severity, transcript}`. Models are black boxes — zero weight tuning; the work
is prompt engineering.

| Piece | Role |
|---|---|
| `ops.py` | `triage` — cross-reference a reading against the patient record via the local LLM |
| `tripwire.py` | hard numeric safety floor (HR/SpO₂/temp/resp bounds) — the watchdog's failsafe |
| `registry.py` | which model + adapter runs `triage` per tier; `type: cloud` routes to GPT |
| `llm_client.py` | OpenAI-compatible client for local tiers (LM Studio / llama.cpp) |
| `cloud_adapter.py` | GPT (Qualcomm AI Inference Suite / OpenAI-compatible); **mock mode** default-on so demos never hang on the network |

Point local tiers at any OpenAI-compatible server via `NEURAROUTE_LOCAL_BASE_URL`
(or use `tools/mock_llm.py`). Weights are gitignored — download per the runbook, never commit.
