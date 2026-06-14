import { useEffect, useCallback } from "react";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import { ChatPanel } from "./ChatPanel";
import { useSettingsStore } from "../../stores/settingsStore";

/**
 * Chat App — standalone chat window.
 *
 * Wraps ChatPanel in a frameless transparent window with:
 * - Draggable header integrated inside ChatPanel
 * - Auto-close on Escape
 * - Window is created visible with transparent background (no white flash)
 */
export function ChatApp() {
  const appWindow = getCurrentWebviewWindow();
  const chatColor = useSettingsStore(
    (s) => s.settings["appearance.chat_color"] || "#0ea5e9",
  );

  // ── Focus window on mount (already visible from creation) ──────────
  useEffect(() => {
    appWindow.setFocus().catch(() => {});
  }, [appWindow]);

  // ── Hide window (keep alive for instant re-show) ──────────────
  const closeChat = useCallback(async () => {
    try {
      await appWindow.hide();
    } catch {
      await appWindow.close().catch(() => {});
    }
  }, [appWindow]);

  // ── Keyboard: Escape to close ────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeChat();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [closeChat]);

  return (
    <div
      className="chat-app-root"
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <ChatPanel onClose={closeChat} chatColor={chatColor} />
    </div>
  );
}
