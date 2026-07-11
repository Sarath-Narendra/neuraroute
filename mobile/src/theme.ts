import { Severity } from "./contracts";

export const C = {
  bg: "#0B0F1A",
  bgElev: "#141A2A",
  card: "#1A2133",
  cardBorder: "#2A3350",
  text: "#E8ECF6",
  textDim: "#96A0B8",
  textFaint: "#5D6884",
  accent: "#4C8DFF",

  normal: "#34C759",
  normalBg: "rgba(52,199,89,0.12)",
  mild: "#FFB020",
  mildBg: "rgba(255,176,32,0.12)",
  emergency: "#FF3B30",
  emergencyBg: "rgba(255,59,48,0.14)",

  aliveDot: "#34C759",
  deadDot: "#5D6884",
};

export function sevColor(s?: Severity): string {
  if (s === "emergency") return C.emergency;
  if (s === "mild") return C.mild;
  if (s === "normal") return C.normal;
  return C.textFaint;
}

export function sevBg(s?: Severity): string {
  if (s === "emergency") return C.emergencyBg;
  if (s === "mild") return C.mildBg;
  if (s === "normal") return C.normalBg;
  return "rgba(93,104,132,0.12)";
}

export function sevLabel(s?: Severity): string {
  if (s === "emergency") return "EMERGENCY";
  if (s === "mild") return "MILD";
  if (s === "normal") return "NORMAL";
  return "—";
}
