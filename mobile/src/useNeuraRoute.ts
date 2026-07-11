import { useCallback, useEffect, useRef, useState } from "react";

import { apiUrl, defaultHost, wsUrl } from "./config";
import { NeuraRouteEvent, Vitals } from "./contracts";
import { fireEmergency, initNotifications } from "./notifications";
import { acknowledge, applyEvent, AppState, initialState, seedRoster } from "./store";

export type ConnState = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface NeuraRoute {
  state: AppState;
  conn: ConnState;
  host: string;
  setHost: (h: string) => void;
  submitReading: (patientId: string, vitals: Vitals) => Promise<boolean>;
  ackEmergency: (patientId: string) => void;
}

export function useNeuraRoute(): NeuraRoute {
  const [state, setState] = useState<AppState>(initialState);
  const [conn, setConn] = useState<ConnState>("connecting");
  const [host, setHost] = useState<string>(defaultHost());

  const lastSosSeq = useRef<number>(0);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    initNotifications();
  }, []);

  // Fire an OS notification whenever a NEW sos lands in state.
  useEffect(() => {
    const sos = state.lastSos;
    if (sos && sos.seq > lastSosSeq.current) {
      lastSosSeq.current = sos.seq;
      const p = state.patients[sos.patient_id];
      fireEmergency(sos.patient_id, p?.name, sos.reason);
    }
  }, [state.lastSos, state.patients]);

  // Load the patient roster (all 10 cards show before any reading arrives).
  const loadRoster = useCallback(async (h: string) => {
    try {
      const res = await fetch(`${apiUrl(h)}/patients`);
      const roster = await res.json();
      if (Array.isArray(roster)) setState((s) => seedRoster(s, roster));
    } catch {
      // engine not reachable yet; the WS layer will keep retrying
    }
  }, []);

  // WebSocket lifecycle, reconnect with backoff. Re-runs when host changes.
  useEffect(() => {
    let cancelled = false;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    // reset per-host view so a host switch doesn't show stale tiers/patients
    setState(initialState());
    lastSosSeq.current = 0;
    loadRoster(host);

    const connect = () => {
      if (cancelled) return;
      setConn(attempt === 0 ? "connecting" : "reconnecting");
      const ws = new WebSocket(wsUrl(host));
      socketRef.current = ws;

      ws.onopen = () => {
        attempt = 0;
        setConn("connected");
        loadRoster(host);
      };
      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data as string) as NeuraRouteEvent;
          setState((s) => applyEvent(s, event));
        } catch {
          // ignore malformed frame
        }
      };
      ws.onerror = () => {
        try {
          ws.close();
        } catch {}
      };
      ws.onclose = () => {
        if (cancelled) return;
        setConn("reconnecting");
        const delay = Math.min(1000 * 2 ** attempt, 8000);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      try {
        socketRef.current?.close();
      } catch {}
    };
  }, [host, loadRoster]);

  const submitReading = useCallback(
    async (patientId: string, vitals: Vitals): Promise<boolean> => {
      try {
        const res = await fetch(`${apiUrl(host)}/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ patient_id: patientId, vitals }),
        });
        return res.ok;
      } catch {
        return false;
      }
    },
    [host],
  );

  const ackEmergency = useCallback((patientId: string) => {
    setState((s) => acknowledge(s, patientId));
  }, []);

  return { state, conn, host, setHost, submitReading, ackEmergency };
}
