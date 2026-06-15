import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useChatStore } from "../../stores/chatStore";
import { useAgent } from "../../hooks/useAgent";
import { useAgentStore } from "../../stores/agentStore";
import { useSettingsStore } from "../../stores/settingsStore";
import { ChatHeader } from "./ChatHeader";
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

  return (
    <div
      className="chat-panel flex flex-col h-full backdrop-blur rounded-2xl shadow-xl overflow-hidden"
      style={{
        background: `rgba(255, 255, 255, ${chatOpacity})`,
        border: `1px solid ${chatColor}33`,
      }}
    >
      <ChatHeader
        label={t("app.name")}
        accentColor={chatColor}
        status={agentStatus === "error" ? "disconnected" : agentStatus}
        onClose={() => onClose?.()}
      />
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
