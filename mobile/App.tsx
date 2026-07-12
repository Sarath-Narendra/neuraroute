import { StatusBar } from "expo-status-bar";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

import { ENGINE_PORT } from "./src/config";
import { LADDER, Severity, TIER_LABEL, Vitals } from "./src/contracts";
import { PatientState } from "./src/store";
import { C, sevBg, sevColor, sevLabel } from "./src/theme";
import { ConnState, useNeuraRoute } from "./src/useNeuraRoute";

const SEV_RANK: Record<string, number> = { emergency: 3, mild: 2, normal: 1 };

export default function App() {
  return (
    <SafeAreaProvider>
      <Board />
    </SafeAreaProvider>
  );
}

function Board() {
  const nr = useNeuraRoute();
  const { state, conn } = nr;
  const [selected, setSelected] = useState<string | null>(null);
  const [showHost, setShowHost] = useState(false);

  const patients = useMemo(() => {
    const list = state.order.map((id) => state.patients[id]).filter(Boolean);
    return list.sort((a, b) => {
      const ae = a.emergencyReason ? 1 : 0;
      const be = b.emergencyReason ? 1 : 0;
      if (ae !== be) return be - ae;
      const ar = SEV_RANK[a.severity ?? ""] ?? 0;
      const br = SEV_RANK[b.severity ?? ""] ?? 0;
      if (ar !== br) return br - ar;
      return (b.updatedAt ?? 0) - (a.updatedAt ?? 0);
    });
  }, [state.order, state.patients]);

  const emergencies = patients.filter((p) => p.emergencyReason);
  const selectedPatient = selected ? state.patients[selected] : null;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <StatusBar style="light" />
      <Header conn={conn} host={nr.host} onEditHost={() => setShowHost(true)} />

      {emergencies.length > 0 && (
        <EmergencyBanner
          patients={emergencies}
          onAck={(id) => nr.ackEmergency(id)}
          onOpen={(id) => setSelected(id)}
        />
      )}

      <TierStrip tiers={state.tiers} />

      <FlatList
        data={patients}
        keyExtractor={(p) => p.patient_id}
        contentContainerStyle={styles.listContent}
        ListHeaderComponent={
          <Text style={styles.sectionLabel}>
            WARD · {patients.length} PATIENTS
            {emergencies.length > 0 ? `  ·  ${emergencies.length} CRITICAL` : ""}
          </Text>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <ActivityIndicator color={C.accent} />
            <Text style={styles.emptyText}>
              {conn === "connected" ? "Waiting for patient roster…" : "Connecting to the engine…"}
            </Text>
            <Text style={styles.emptyHint}>Engine: {nr.host}:{ENGINE_PORT}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <PatientCard patient={item} onPress={() => setSelected(item.patient_id)} />
        )}
      />

      <PatientModal
        patient={selectedPatient}
        onClose={() => setSelected(null)}
        onSubmit={nr.submitReading}
        onAck={nr.ackEmergency}
      />
      <HostModal
        visible={showHost}
        host={nr.host}
        onClose={() => setShowHost(false)}
        onSave={(h) => {
          nr.setHost(h);
          setShowHost(false);
        }}
      />
    </SafeAreaView>
  );
}

/* ------------------------------------------------------------------ header */

function Header({ conn, host, onEditHost }: { conn: ConnState; host: string; onEditHost: () => void }) {
  const color =
    conn === "connected" ? C.normal : conn === "reconnecting" ? C.mild : C.textFaint;
  const label =
    conn === "connected" ? "LIVE" : conn === "reconnecting" ? "RECONNECTING" : "OFFLINE";
  return (
    <View style={styles.header}>
      <View>
        <Text style={styles.brand}>
          Neura<Text style={{ color: C.accent }}>Route</Text>
        </Text>
        <Text style={styles.subBrand}>Night ward · triage monitor</Text>
      </View>
      <TouchableOpacity style={styles.connPill} onPress={onEditHost} activeOpacity={0.7}>
        <View style={[styles.dot, { backgroundColor: color }]} />
        <Text style={[styles.connText, { color }]}>{label}</Text>
      </TouchableOpacity>
    </View>
  );
}

/* --------------------------------------------------------------- emergency */

function EmergencyBanner({
  patients,
  onAck,
  onOpen,
}: {
  patients: PatientState[];
  onAck: (id: string) => void;
  onOpen: (id: string) => void;
}) {
  const top = patients[0];
  return (
    <View style={styles.banner}>
      <View style={styles.bannerPulse} />
      <Pressable style={{ flex: 1 }} onPress={() => onOpen(top.patient_id)}>
        <Text style={styles.bannerTitle}>
          🚨 EMERGENCY{patients.length > 1 ? ` ·  ${patients.length} patients` : ""}
        </Text>
        <Text style={styles.bannerPatient}>
          {top.name ? `${top.name} · ` : ""}
          {top.patient_id}
        </Text>
        <Text style={styles.bannerReason} numberOfLines={2}>
          {top.emergencyReason}
        </Text>
      </Pressable>
      <TouchableOpacity style={styles.ackBtn} onPress={() => onAck(top.patient_id)}>
        <Text style={styles.ackBtnText}>ACK</Text>
      </TouchableOpacity>
    </View>
  );
}

/* -------------------------------------------------------------- tier strip */

function TierStrip({ tiers }: { tiers: Record<string, { alive: boolean }> }) {
  return (
    <View style={styles.tierStrip}>
      {LADDER.map((t, i) => {
        const alive = tiers[t.id]?.alive;
        return (
          <View key={t.id} style={styles.tierItem}>
            <View style={styles.tierRow}>
              <View style={[styles.dot, { backgroundColor: alive ? C.aliveDot : C.deadDot }]} />
              <Text style={[styles.tierLabel, { color: alive ? C.text : C.textFaint }]}>
                {t.short}
              </Text>
            </View>
            {i < LADDER.length - 1 && <Text style={styles.tierArrow}>›</Text>}
          </View>
        );
      })}
    </View>
  );
}

/* ------------------------------------------------------------ patient card */

function Badge({ severity }: { severity?: Severity }) {
  return (
    <View style={[styles.badge, { backgroundColor: sevBg(severity) }]}>
      <Text style={[styles.badgeText, { color: sevColor(severity) }]}>{sevLabel(severity)}</Text>
    </View>
  );
}

function VitalsRow({ vitals }: { vitals?: Vitals }) {
  if (!vitals) return <Text style={styles.vitalsNone}>no reading yet</Text>;
  const parts: string[] = [];
  if (vitals.hr != null) parts.push(`HR ${vitals.hr}`);
  if (vitals.spo2 != null) parts.push(`SpO₂ ${vitals.spo2}%`);
  if (vitals.temp_c != null) parts.push(`${vitals.temp_c}°`);
  if (vitals.resp_rate != null) parts.push(`RR ${vitals.resp_rate}`);
  return <Text style={styles.vitals}>{parts.join("   ")}</Text>;
}

function PatientCard({ patient, onPress }: { patient: PatientState; onPress: () => void }) {
  const border = patient.emergencyReason ? C.emergency : C.cardBorder;
  return (
    <TouchableOpacity
      style={[styles.card, { borderColor: border }]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <View style={[styles.sevStripe, { backgroundColor: sevColor(patient.severity) }]} />
      <View style={{ flex: 1 }}>
        <View style={styles.cardTop}>
          <Text style={styles.patientName}>
            {patient.name ?? patient.patient_id}
            {patient.name ? <Text style={styles.patientId}>  {patient.patient_id}</Text> : null}
          </Text>
          <Badge severity={patient.severity} />
        </View>
        <VitalsRow vitals={patient.vitals} />
        <View style={styles.cardBottom}>
          {patient.status === "analyzing" ? (
            <View style={styles.analyzing}>
              <ActivityIndicator size="small" color={C.accent} />
              <Text style={styles.analyzingText}>
                triaging{patient.tier ? ` · ${TIER_LABEL[patient.tier] ?? patient.tier}` : ""}…
              </Text>
            </View>
          ) : patient.tier ? (
            <Text style={styles.cardTier}>via {TIER_LABEL[patient.tier] ?? patient.tier}</Text>
          ) : (
            <Text style={styles.cardTier}>—</Text>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
}

/* ----------------------------------------------------------- patient modal */

const PRESETS: { label: string; tone: Severity; vitals: Vitals }[] = [
  { label: "Normal", tone: "normal", vitals: { hr: 78, spo2: 96, temp_c: 36.8, resp_rate: 16 } },
  { label: "Concerning", tone: "mild", vitals: { hr: 118, spo2: 92, temp_c: 38.6, resp_rate: 23 } },
  { label: "Critical", tone: "emergency", vitals: { hr: 176, spo2: 79, temp_c: 37.0, resp_rate: 32 } },
];

const FIELDS: { key: keyof Vitals; label: string }[] = [
  { key: "hr", label: "HR" },
  { key: "spo2", label: "SpO₂" },
  { key: "temp_c", label: "Temp °C" },
  { key: "resp_rate", label: "Resp" },
  { key: "bp_sys", label: "BP sys" },
  { key: "bp_dia", label: "BP dia" },
];

function PatientModal({
  patient,
  onClose,
  onSubmit,
  onAck,
}: {
  patient: PatientState | null;
  onClose: () => void;
  onSubmit: (id: string, v: Vitals) => Promise<boolean>;
  onAck: (id: string) => void;
}) {
  const [form, setForm] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);

  const applyPreset = (v: Vitals) => {
    const next: Record<string, string> = {};
    for (const [k, val] of Object.entries(v)) next[k] = String(val);
    setForm(next);
  };

  const submit = async () => {
    if (!patient) return;
    const vitals: Vitals = {};
    for (const f of FIELDS) {
      const raw = form[f.key as string];
      if (raw !== undefined && raw !== "") {
        const n = Number(raw);
        if (!Number.isNaN(n)) vitals[f.key] = n;
      }
    }
    if (Object.keys(vitals).length === 0) return;
    setSending(true);
    await onSubmit(patient.patient_id, vitals);
    setSending(false);
  };

  return (
    <Modal visible={!!patient} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalWrap}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalKav}>
          <View style={styles.modalCard}>
            <View style={styles.modalHandle} />
            {patient && (
              <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
                <View style={styles.modalHead}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.modalName}>{patient.name ?? patient.patient_id}</Text>
                    <Text style={styles.modalMeta}>
                      {patient.patient_id}
                      {patient.age ? ` · ${patient.age}y` : ""}
                      {patient.conditions?.length ? ` · ${patient.conditions.join(", ")}` : ""}
                    </Text>
                  </View>
                  <Badge severity={patient.severity} />
                </View>

                {patient.emergencyReason && (
                  <TouchableOpacity
                    style={styles.modalEmergency}
                    onPress={() => onAck(patient.patient_id)}
                  >
                    <Text style={styles.modalEmergencyText}>🚨 {patient.emergencyReason}</Text>
                    <Text style={styles.modalEmergencyAck}>tap to acknowledge</Text>
                  </TouchableOpacity>
                )}

                <Text style={styles.modalSection}>LATEST TRIAGE</Text>
                <View style={styles.transcriptBox}>
                  <VitalsRow vitals={patient.vitals} />
                  <Text style={styles.transcript}>
                    {patient.transcript ?? "No triage yet. Submit a reading below."}
                  </Text>
                  {patient.tier && (
                    <Text style={styles.transcriptTier}>
                      — {TIER_LABEL[patient.tier] ?? patient.tier}
                    </Text>
                  )}
                </View>

                <Text style={styles.modalSection}>SUBMIT A READING</Text>
                <View style={styles.presetRow}>
                  {PRESETS.map((p) => (
                    <TouchableOpacity
                      key={p.label}
                      style={[styles.preset, { borderColor: sevColor(p.tone) }]}
                      onPress={() => applyPreset(p.vitals)}
                    >
                      <Text style={[styles.presetText, { color: sevColor(p.tone) }]}>{p.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <View style={styles.fieldGrid}>
                  {FIELDS.map((f) => (
                    <View key={f.key as string} style={styles.field}>
                      <Text style={styles.fieldLabel}>{f.label}</Text>
                      <TextInput
                        style={styles.input}
                        keyboardType="numeric"
                        placeholder="—"
                        placeholderTextColor={C.textFaint}
                        value={form[f.key as string] ?? ""}
                        onChangeText={(t) => setForm((s) => ({ ...s, [f.key as string]: t }))}
                      />
                    </View>
                  ))}
                </View>

                <TouchableOpacity
                  style={[styles.submitBtn, sending && { opacity: 0.6 }]}
                  onPress={submit}
                  disabled={sending}
                >
                  {sending ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.submitText}>SEND READING</Text>
                  )}
                </TouchableOpacity>

                <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
                  <Text style={styles.closeText}>Close</Text>
                </TouchableOpacity>
              </ScrollView>
            )}
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

/* -------------------------------------------------------------- host modal */

function HostModal({
  visible,
  host,
  onClose,
  onSave,
}: {
  visible: boolean;
  host: string;
  onClose: () => void;
  onSave: (h: string) => void;
}) {
  const [value, setValue] = useState(host);
  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <Pressable style={styles.hostWrap} onPress={onClose}>
        <Pressable style={styles.hostCard}>
          <Text style={styles.modalSection}>ENGINE HOST</Text>
          <Text style={styles.hostHint}>
            The laptop's hotspot IP running the engine. Auto-detected from the Expo host; override if
            needed.
          </Text>
          <TextInput
            style={styles.hostInput}
            value={value}
            onChangeText={setValue}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="numbers-and-punctuation"
            placeholder="192.168.x.x"
            placeholderTextColor={C.textFaint}
          />
          <View style={styles.hostBtns}>
            <TouchableOpacity style={styles.hostCancel} onPress={onClose}>
              <Text style={styles.closeText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.hostSave} onPress={() => onSave(value.trim())}>
              <Text style={styles.submitText}>Connect</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

/* -------------------------------------------------------------------- style */

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 12,
  },
  brand: { color: C.text, fontSize: 26, fontWeight: "800", letterSpacing: -0.5 },
  subBrand: { color: C.textFaint, fontSize: 12, marginTop: 2, letterSpacing: 0.3 },
  connPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: C.bgElev,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  dot: { width: 8, height: 8, borderRadius: 4 },
  connText: { fontSize: 11, fontWeight: "700", letterSpacing: 0.5 },

  banner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.emergencyBg,
    borderColor: C.emergency,
    borderWidth: 1.5,
    marginHorizontal: 16,
    marginBottom: 10,
    borderRadius: 16,
    padding: 14,
    overflow: "hidden",
  },
  bannerPulse: { position: "absolute", left: 0, top: 0, bottom: 0, width: 5, backgroundColor: C.emergency },
  bannerTitle: { color: C.emergency, fontWeight: "800", fontSize: 13, letterSpacing: 0.5 },
  bannerPatient: { color: C.text, fontWeight: "700", fontSize: 17, marginTop: 3 },
  bannerReason: { color: C.textDim, fontSize: 13, marginTop: 2 },
  ackBtn: {
    backgroundColor: C.emergency,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginLeft: 10,
  },
  ackBtnText: { color: "#fff", fontWeight: "800", fontSize: 13 },

  tierStrip: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginHorizontal: 16,
    marginBottom: 12,
    backgroundColor: C.bgElev,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  tierItem: { flexDirection: "row", alignItems: "center" },
  tierRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  tierLabel: { fontSize: 13, fontWeight: "600" },
  tierArrow: { color: C.textFaint, fontSize: 18, marginHorizontal: 8 },

  sectionLabel: {
    color: C.textFaint,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    marginBottom: 10,
    marginLeft: 4,
  },
  listContent: { paddingHorizontal: 16, paddingBottom: 40 },

  card: {
    flexDirection: "row",
    backgroundColor: C.card,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 10,
    overflow: "hidden",
  },
  sevStripe: { width: 4 },
  cardTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: 12,
    paddingHorizontal: 14,
  },
  patientName: { color: C.text, fontSize: 16, fontWeight: "700" },
  patientId: { color: C.textFaint, fontSize: 13, fontWeight: "500" },
  badge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 11, fontWeight: "800", letterSpacing: 0.5 },
  vitals: { color: C.textDim, fontSize: 14, paddingHorizontal: 14, paddingTop: 6, fontVariant: ["tabular-nums"] },
  vitalsNone: { color: C.textFaint, fontSize: 13, paddingHorizontal: 14, paddingTop: 6, fontStyle: "italic" },
  cardBottom: { paddingHorizontal: 14, paddingTop: 6, paddingBottom: 12 },
  cardTier: { color: C.textFaint, fontSize: 12 },
  analyzing: { flexDirection: "row", alignItems: "center", gap: 8 },
  analyzingText: { color: C.accent, fontSize: 12, fontWeight: "600" },

  empty: { alignItems: "center", paddingTop: 80, gap: 12 },
  emptyText: { color: C.textDim, fontSize: 14 },
  emptyHint: { color: C.textFaint, fontSize: 12 },

  modalWrap: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  modalKav: { flex: 1, justifyContent: "flex-end" },
  modalCard: {
    backgroundColor: C.bgElev,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 20,
    paddingBottom: 24,
    paddingTop: 10,
    maxHeight: "92%",
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  modalHandle: {
    alignSelf: "center",
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: C.cardBorder,
    marginBottom: 14,
  },
  modalHead: { flexDirection: "row", alignItems: "center", marginBottom: 14 },
  modalName: { color: C.text, fontSize: 22, fontWeight: "800" },
  modalMeta: { color: C.textDim, fontSize: 13, marginTop: 3 },
  modalEmergency: {
    backgroundColor: C.emergencyBg,
    borderColor: C.emergency,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
  },
  modalEmergencyText: { color: C.emergency, fontWeight: "700", fontSize: 14 },
  modalEmergencyAck: { color: C.textDim, fontSize: 11, marginTop: 4 },
  modalSection: {
    color: C.textFaint,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    marginBottom: 8,
    marginTop: 4,
  },
  transcriptBox: {
    backgroundColor: C.card,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: C.cardBorder,
    marginBottom: 8,
  },
  transcript: { color: C.text, fontSize: 15, lineHeight: 22, marginTop: 8 },
  transcriptTier: { color: C.textFaint, fontSize: 12, marginTop: 10, fontStyle: "italic" },

  presetRow: { flexDirection: "row", gap: 8, marginBottom: 12 },
  preset: { flex: 1, borderWidth: 1, borderRadius: 10, paddingVertical: 10, alignItems: "center" },
  presetText: { fontSize: 13, fontWeight: "700" },
  fieldGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 16 },
  field: { width: "30%", flexGrow: 1 },
  fieldLabel: { color: C.textDim, fontSize: 11, marginBottom: 4, fontWeight: "600" },
  input: {
    backgroundColor: C.card,
    borderColor: C.cardBorder,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: C.text,
    fontSize: 16,
    fontVariant: ["tabular-nums"],
  },
  submitBtn: { backgroundColor: C.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  submitText: { color: "#fff", fontWeight: "800", fontSize: 15, letterSpacing: 0.5 },
  closeBtn: { alignItems: "center", paddingVertical: 14, marginTop: 4 },
  closeText: { color: C.textDim, fontSize: 15, fontWeight: "600" },

  hostWrap: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "center", padding: 24 },
  hostCard: { backgroundColor: C.bgElev, borderRadius: 20, padding: 20, borderWidth: 1, borderColor: C.cardBorder },
  hostHint: { color: C.textDim, fontSize: 13, lineHeight: 19, marginBottom: 14 },
  hostInput: {
    backgroundColor: C.card,
    borderColor: C.cardBorder,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: C.text,
    fontSize: 17,
    marginBottom: 16,
  },
  hostBtns: { flexDirection: "row", gap: 12 },
  hostCancel: { flex: 1, alignItems: "center", paddingVertical: 14, borderRadius: 12, backgroundColor: C.card },
  hostSave: { flex: 1, alignItems: "center", paddingVertical: 14, borderRadius: 12, backgroundColor: C.accent },
});
