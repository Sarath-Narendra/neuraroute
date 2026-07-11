# dashboard/ — Live Dashboard (owner: Abhiram)

Vite + React + Tailwind (+ShadCN). The visualization **is** the product — big fonts, high
contrast, reads from 3 m on a projector.

- Auto-reconnecting WebSocket client; graceful "disconnected" state (never a crash).
- 4 device tiles (name, battery bar, CPU/NPU load, green/red status).
- DAG animation: 5 nodes light up on the device that ran them, with the reason string.
- Scrolling decision log; metrics panel (reads `metrics/metrics.json`).
- Policy toggle (speed-first ↔ battery-saver → POST to engine).
- Failover theater: tile → red, task chip flies to the new device.

Test against `contracts/fake_engine.py` (canned event stream). Insurance path: if FastAPI's
WS fights us, ship an MQTT→WS bridge in Node.
