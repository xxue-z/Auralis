import { useState } from "react";
import { useTranslation } from "react-i18next";
import { LanguageSelector } from "./LanguageSelector";
import { ModelConfig } from "./ModelConfig";

type Section = "general" | "model" | null;

interface Props {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: Props) {
  const { t } = useTranslation();
  const [section, setSection] = useState<Section>(null);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
      <div className="w-96 max-h-[80vh] bg-white/95 backdrop-blur rounded-2xl shadow-xl overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-bold text-gray-800">⚙️ {t("settings.title")}</h2>
          <button
            onClick={onClose}
            className="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            ✕
          </button>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {/* 语言设置 */}
          <SettingsSection
            title={`🌐 ${t("settings.language.label")}`}
            isOpen={section === "general"}
            onToggle={() => setSection(section === "general" ? null : "general")}
          >
            <LanguageSelector />
          </SettingsSection>

          {/* 模型配置 */}
          <SettingsSection
            title={`🤖 AI 模型`}
            isOpen={section === "model"}
            onToggle={() => setSection(section === "model" ? null : "model")}
          >
            <ModelConfig />
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}

function SettingsSection({
  title,
  isOpen,
  onToggle,
  children,
}: {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span>{title}</span>
        <span className="text-gray-400">{isOpen ? "▲" : "▼"}</span>
      </button>
      {isOpen && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}
