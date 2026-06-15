import { useState, useCallback } from "react";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";

interface Props {
  label: string;
  accentColor: string;
  status: "connected" | "connecting" | "disconnected";
  onClose: () => void;
}

/**
 * Chat window header — draggable title bar with pin and close buttons.
 */
export function ChatHeader({ label, accentColor, status, onClose }: Props) {
  const [isPinned, setIsPinned] = useState(false);

  const togglePin = useCallback(async () => {
    const next = !isPinned;
    setIsPinned(next);
    try {
      const win = getCurrentWebviewWindow();
      await win.setAlwaysOnTop(next);
    } catch {
      // ignore
    }
  }, [isPinned]);

  const statusDot = {
    connected: "🟢",
    connecting: "🟡",
    disconnected: "🔴",
  }[status];

  return (
    <div
      className="chat-header-root"
      data-tauri-drag-region
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 12px",
        background: `rgba(${parseInt(accentColor.slice(1, 3), 16)}, ${parseInt(accentColor.slice(3, 5), 16)}, ${parseInt(accentColor.slice(5, 7), 16)}, 0.08)`,
        borderBottom: `1px solid rgba(${parseInt(accentColor.slice(1, 3), 16)}, ${parseInt(accentColor.slice(3, 5), 16)}, ${parseInt(accentColor.slice(5, 7), 16)}, 0.2)`,
        borderRadius: "16px 16px 0 0",
        height: 36,
        userSelect: "none",
      }}
    >
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: accentColor,
        }}
      >
        {statusDot} {label}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
        <button
          data-tauri-no-drag
          onClick={togglePin}
          title={isPinned ? "取消置顶" : "置顶"}
          style={{
            width: 24,
            height: 24,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "none",
            background: "transparent",
            color: isPinned ? accentColor : "#999",
            cursor: "pointer",
            borderRadius: 12,
            fontSize: 14,
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLElement).style.background = "#f0f0f0";
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLElement).style.background = "transparent";
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill={isPinned ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="8" r="4" />
            <path d="M12 12v10" />
            <path d="M8 22h8" />
          </svg>
        </button>
        <button
          data-tauri-no-drag
          onClick={onClose}
          style={{
            width: 24,
            height: 24,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "none",
            background: "transparent",
            color: "#999",
            cursor: "pointer",
            borderRadius: 12,
            fontSize: 14,
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLElement).style.background = "#f0f0f0";
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLElement).style.background = "transparent";
          }}
          title="Close"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
