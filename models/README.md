# models/ — Model Ops & Cloud (owner: Eswar)

All 5 ops behind one signature everyone calls: **`run_model(op, payload) -> result`**.
Models are black boxes — zero weight tuning; the work is prompt engineering.

| op | Implementation |
|---|---|
| `extract_text` | PyMuPDF text extraction |
| `summarize` | small quantized LLM (Phi-3-mini / Llama-3.2-3B Q4 via llama.cpp or LM Studio), prompt A |
| `flag_risk` | same local LLM, prompt B |
| `patient_explainer` | same local LLM, prompt C (stretch: small Sarvam model on-edge for local language) |
| `population_stats` | cloud LLM call (non-sensitive → cloud-eligible) |

- `cloud_adapter.py` — OpenAI-compatible client (Qualcomm AI Inference Suite); endpoint/key
  from env; **mock mode** (canned response after 2 s) so demos never hang on network.

Weights are gitignored — download per the runbook, never commit.
