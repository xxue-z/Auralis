import { Message } from "../../stores/chatStore";

interface Props {
  message: Message;
  chatColor?: string;
}

export function MessageBubble({ message, chatColor = "#0ea5e9" }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-2 mb-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* 头像 */}
      <div
        className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-sm ${
          isUser ? "bg-gray-200" : "bg-primary-100"
        }`}
      >
        {isUser ? "👤" : "🧚"}
      </div>

      {/* 气泡 */}
      <div
        className={`max-w-[75%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "text-white rounded-br-md"
            : "bg-gray-100 text-gray-800 rounded-bl-md"
        } ${message.status === "error" ? "bg-red-100 text-red-600" : ""}`}
        style={isUser ? { background: chatColor } : undefined}
      >
        {message.content}
        {message.status === "streaming" && (
          <span className="inline-block w-1.5 h-3.5 bg-gray-400 ml-0.5 animate-pulse" />
        )}
      </div>
    </div>
  );
}
