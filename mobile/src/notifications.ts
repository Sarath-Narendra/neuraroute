/**
 * Notifications shim for Expo Go (SDK 53+).
 *
 * `expo-notifications` now throws in Expo Go the moment its module initializes:
 *   "Android Push notifications … was removed from Expo Go. Use a development build."
 * Even a plain `import * as Notifications from "expo-notifications"` pulls in that push
 * path and crashes the app on launch (the red "[runtime not ready]" screen).
 *
 * The demo does NOT need OS-level notifications — the in-app EmergencyBanner in App.tsx
 * already surfaces the SOS visually the instant it lands. These no-ops keep the app
 * running in Expo Go.
 *
 * To restore real on-device OS notifications later, make a DEVELOPMENT BUILD
 * (`npx expo prebuild` / EAS build) instead of using Expo Go, then re-add the original
 * expo-notifications implementation (local notifications, not push — see git history).
 */

export async function initNotifications(): Promise<boolean> {
  return false; // no OS notifications in Expo Go; the in-app banner still works
}

export async function fireEmergency(
  _patientId: string,
  _patientName: string | undefined,
  _reason: string,
): Promise<void> {
  // no-op in Expo Go — the in-app EmergencyBanner handles the visual alert
}
