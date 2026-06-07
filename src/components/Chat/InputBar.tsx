import { useState, KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function InputBar({ onSend, disabled }: Props) {
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
                   focus:outline-none focus:border-primary-400 bg-white/80
                   disabled:opacity-50"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-primary-500
                   rounded-full hover:bg-primary-600 disabled:opacity-50
                   disabled:cursor-not-allowed transition-colors"
      >
        {t("chat.send")}
      </button>
    </div>
  );
}
