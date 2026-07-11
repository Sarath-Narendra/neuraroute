import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

/**
 * Local (on-device) emergency notifications. Deliberately NOT push notifications:
 * the failsafe fires exactly when the internet is down, so delivery must not depend
 * on a cloud push server. The app raises the OS notification itself off the WS event.
 */

// Show the alert even when the app is foregrounded (doctor may be staring at the board).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    // new API (SDK 53+)
    shouldShowBanner: true,
    shouldShowList: true,
    // legacy field kept for safety on older runtimes
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const CHANNEL_ID = "neuraroute-emergency";

export async function initNotifications(): Promise<boolean> {
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync(CHANNEL_ID, {
        name: "Emergencies",
        importance: Notifications.AndroidImportance.MAX,
        sound: "default",
        vibrationPattern: [0, 400, 200, 400],
        lightColor: "#FF3B30",
        bypassDnd: true,
      });
    }
    const settings = await Notifications.getPermissionsAsync();
    let status = settings.status;
    if (status !== "granted") {
      const req = await Notifications.requestPermissionsAsync();
      status = req.status;
    }
    return status === "granted";
  } catch {
    return false; // web / unsupported runtime — the in-app banner still works
  }
}

export async function fireEmergency(
  patientId: string,
  patientName: string | undefined,
  reason: string,
): Promise<void> {
  const who = patientName ? `${patientName} (${patientId})` : patientId;
  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: `🚨 EMERGENCY — ${who}`,
        body: reason || "Extreme vitals detected. Attend immediately.",
        sound: "default",
        priority: Notifications.AndroidNotificationPriority.MAX,
        vibrate: [0, 400, 200, 400],
        data: { patientId },
      },
      trigger: null, // fire immediately
      ...(Platform.OS === "android" ? { identifier: undefined } : {}),
    } as any);
  } catch {
    // never let a notification failure crash the stream handler
  }
}
