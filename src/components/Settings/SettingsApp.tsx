import { useEffect, useCallback } from "react";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import { SettingsPanel } from "./SettingsPanel";

/**
 * Settings App — standalone settings window.
 *
 * Wraps SettingsPanel in a frameless transparent window with:
 * - Draggable header (set via data-tauri-drag-region in SettingsPanel)
 * - Auto-hide on Escape (keeps WebView2 alive for instant re-show)
 * - Focus on mount (window is pre-created hidden by PetApp)
 */
export function SettingsApp() {
  const appWindow = getCurrentWebviewWindow();

  // ── Focus window on mount (already shown by PetApp) ────────
  useEffect(() => {
    appWindow.setFocus().catch(() => {});
  }, [appWindow]);

  // ── Hide window (keep alive for instant re-show) ───────────
  const closeSettings = useCallback(async () => {
    try {
      await appWindow.hide();
    } catch {
      await appWindow.close().catch(() => {});
    }
  }, [appWindow]);

  // ── Keyboard: Escape to hide ────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeSettings();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [closeSettings]);

  return (
    <div
      className="settings-app-root"
      style={{
        width: "100vw",
        height: "100vh",
      }}
    >
      <SettingsPanel onClose={closeSettings} />
    </div>
  );
}
