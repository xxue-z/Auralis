import { useState, KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  chatColor?: string;
}

export function InputBar({ onSend, disabled, chatColor = "#0ea5e9" }: Props) {
  const { t } = useTranslation();
  const [input, setInput] = useState("");

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-2 p-2 border-t border-gray-200">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("chat.placeholder")}
        disabled={disabled}
        className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-full
                   focus:outline-none bg-white/80 disabled:opacity-50"
        style={{ outlineColor: chatColor }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="px-4 py-2 text-sm font-medium text-white rounded-full
                   hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        style={{ background: chatColor }}
      >
        {t("chat.send")}
      </button>
    </div>
  );
}
