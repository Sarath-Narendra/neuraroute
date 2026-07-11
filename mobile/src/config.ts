import Constants from "expo-constants";

/**
 * Where the NeuraRoute engine lives. In the common demo setup the engine runs on
 * the SAME laptop that serves the Expo bundle, so we default to the Expo dev-server's
 * host (the laptop's hotspot IP) on the engine port — zero config. The user can still
 * override the host in-app if the engine runs elsewhere.
 */
// 8080: the inference module's /infer servers own 8000 (laptop) and 8001 (cloud).
const ENGINE_PORT = 8080;

function devServerHost(): string | null {
  // e.g. "192.168.43.1:8081" (Metro) -> "192.168.43.1"
  const hostUri =
    (Constants.expoConfig as any)?.hostUri ??
    (Constants as any)?.expoGoConfig?.hostUri ??
    (Constants as any)?.manifest?.debuggerHost ??
    null;
  if (!hostUri || typeof hostUri !== "string") return null;
  const host = hostUri.split(":")[0];
  return host || null;
}

/** An env override wins (set EXPO_PUBLIC_NEURAROUTE_HOST=<ip> before `expo start`). */
const ENV_HOST = process.env.EXPO_PUBLIC_NEURAROUTE_HOST || null;

export function defaultHost(): string {
  return ENV_HOST || devServerHost() || "localhost";
}

export function wsUrl(host: string): string {
  return `ws://${host}:${ENGINE_PORT}/ws`;
}

export function apiUrl(host: string): string {
  return `http://${host}:${ENGINE_PORT}`;
}

export { ENGINE_PORT };
