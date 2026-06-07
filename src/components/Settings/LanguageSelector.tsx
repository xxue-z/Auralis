import { useTranslation } from "react-i18next";
import { useSettingsStore } from "../../stores/settingsStore";

const LANGUAGES = [
  { code: "en-US", name: "English", nativeName: "English" },
  { code: "zh-CN", name: "Chinese (Simplified)", nativeName: "中文（简体）" },
];

export function LanguageSelector() {
  const { t } = useTranslation();
  const locale = useSettingsStore((s) => s.locale);
  const setLocale = useSettingsStore((s) => s.setLocale);

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-gray-500">{t("settings.language.label")}:</label>
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value)}
        className="text-xs px-2 py-1 border border-gray-200 rounded bg-white/80
                   focus:outline-none focus:border-primary-400"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.nativeName}
          </option>
        ))}
      </select>
    </div>
  );
}
