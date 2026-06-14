import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useChatStore } from "../../stores/chatStore";
import { useAgent } from "../../hooks/useAgent";
import { useAgentStore } from "../../stores/agentStore";
import { useSettingsStore } from "../../stores/settingsStore";
import { MessageBubble } from "./MessageBubble";
import { InputBar } from "./InputBar";

interface ChatPanelProps {
  onClose?: () => void;
  chatColor?: string;
}

export function ChatPanel({ onClose, chatColor: propColor }: ChatPanelProps = {}) {
  const { t } = useTranslation();
  const messages = useChatStore((s) => s.messages);
  const isThinking = useChatStore((s) => s.isThinking);
  const agentStatus = useAgentStore((s) => s.status);
  const settingsColor = useSettingsStore((s) => s.settings["appearance.chat_color"] || "#0ea5e9");
  const chatColor = propColor || settingsColor;
  const chatOpacity = useSettingsStore((s) => s.settings["appearance.chat_opacity"] || 0.9);
  const { sendMessage, connect } = useAgent();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    connect();
  }, [connect]);

  // 将 hex 颜色转换为 rgba
  const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  return (
    <div
      className="chat-panel flex flex-col h-full backdrop-blur rounded-2xl shadow-xl overflow-hidden"
      style={{ background: hexToRgba("#ffffff", chatOpacity) }}
    >
      <div
        data-tauri-drag-region
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: hexToRgba(chatColor, 0.2), background: hexToRgba(chatColor, 0.05), minHeight: 36, userSelect: "none" }}
      >
        <span className="text-xs font-medium" style={{ color: chatColor }}>
          {agentStatus === "connected"
            ? "🟢 " + t("app.name")
            : agentStatus === "connecting"
            ? "🟡 " + t("chat.connecting")
            : "🔴 " + t("chat.disconnected")}
        </span>
        {onClose && (
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
              lineHeight: 1,
              padding: 0,
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.background = hexToRgba(chatColor, 0.1);
              (e.target as HTMLElement).style.color = chatColor;
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.background = "transparent";
              (e.target as HTMLElement).style.color = "#999";
            }}
            title="Close"
          >
            ✕
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">
            {t("character.greeting")}
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} chatColor={chatColor} />
        ))}
        {isThinking && (
          <div className="text-center text-gray-400 text-xs animate-pulse">
            {t("chat.thinking")}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <InputBar onSend={sendMessage} disabled={agentStatus !== "connected"} chatColor={chatColor} />
    </div>
  );
}
