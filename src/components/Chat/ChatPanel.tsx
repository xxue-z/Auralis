import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useChatStore } from "../../stores/chatStore";
import { useAgent } from "../../hooks/useAgent";
import { useAgentStore } from "../../stores/agentStore";
import { MessageBubble } from "./MessageBubble";
import { InputBar } from "./InputBar";

export function ChatPanel() {
  const { t } = useTranslation();
  const messages = useChatStore((s) => s.messages);
  const isThinking = useChatStore((s) => s.isThinking);
  const agentStatus = useAgentStore((s) => s.status);
  const { sendMessage, connect } = useAgent();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <div className="chat-panel flex flex-col h-full bg-white/90 backdrop-blur rounded-2xl shadow-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white/50">
        <span className="text-xs font-medium text-gray-500">
          {agentStatus === "connected"
            ? "🟢 " + t("app.name")
            : agentStatus === "connecting"
            ? "🟡 " + t("chat.connecting")
            : "🔴 " + t("chat.disconnected")}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">
            {t("character.greeting")}
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isThinking && (
          <div className="text-center text-gray-400 text-xs animate-pulse">
            {t("chat.thinking")}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <InputBar onSend={sendMessage} disabled={agentStatus !== "connected"} />
    </div>
  );
}
