import { useState } from "react";
import { useTranslation } from "react-i18next";
import { LanguageSelector } from "./LanguageSelector";
import { ModelConfig } from "./ModelConfig";
import { ThemeConfig } from "./ThemeConfig";
import { VoiceConfig } from "./VoiceConfig";

type Section = "general" | "model" | "theme" | "voice";

const NAV_ITEMS: {
  key: Section;
  icon: string;
  labelKey: string;
  fallback: string;
}[] = [
  { key: "general", icon: "🌐", labelKey: "settings.language.label", fallback: "Language" },
  { key: "model", icon: "🤖", labelKey: "settings.model", fallback: "Model" },
  { key: "theme", icon: "🎨", labelKey: "settings.theme", fallback: "Appearance" },
  { key: "voice", icon: "🎤", labelKey: "settings.voice", fallback: "Voice" },
];

interface Props {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: Props) {
  const { t } = useTranslation();
  const [section, setSection] = useState<Section>("general");

  return (
    <div className="flex flex-col h-screen w-screen bg-white">
      <div
        data-tauri-drag-region
        className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 shrink-0"
      >
        <h2 className="text-sm font-bold text-gray-800">
          ⚙️ {t("settings.title")}
        </h2>
        <button
          onClick={onClose}
          className="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
        >
          ✕
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <nav className="w-36 shrink-0 bg-gray-50/80 border-r border-gray-200 py-3 px-2 flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const label = item.labelKey ? t(item.labelKey) : item.fallback;
            const isActive = section === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setSection(item.key)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 font-semibold"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                }`}
              >
                <span className="text-sm leading-none">{item.icon}</span>
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        <div className="flex-1 overflow-y-auto p-5">
          {section === "general" && <LanguageSelector />}
          {section === "model" && <ModelConfig />}
          {section === "theme" && <ThemeConfig />}
          {section === "voice" && <VoiceConfig />}
        </div>
      </div>
    </div>
  );
}
