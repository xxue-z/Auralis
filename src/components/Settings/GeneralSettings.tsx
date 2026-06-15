import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { useSettingsStore } from "../../stores/settingsStore";

const LANGUAGES = [
  { code: "en-US", name: "English", nativeName: "English" },
  { code: "zh-CN", name: "Chinese (Simplified)", nativeName: "中文（简体）" },
];

export function GeneralSettings() {
  const { t } = useTranslation();
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [defaultPath, setDefaultPath] = useState("");
  const [migrating, setMigrating] = useState(false);

  useEffect(() => {
    invoke<string>("get_app_data_dir").then(setDefaultPath).catch(() => {});
  }, []);

  const displayPath = settings["general.extensions_path"] || defaultPath;

  const handleSelectFolder = async () => {
    const selected = await open({
      multiple: false,
      directory: true,
    });
    if (!selected || selected === displayPath) return;

    setMigrating(true);
    try {
      const oldPath = settings["general.extensions_path"] || defaultPath;
      if (oldPath) {
        await invoke("migrate_extensions", { oldPath, newPath: selected });
      }
      setSetting("general.extensions_path", selected);
    } catch (e: any) {
      console.error("迁移扩展文件夹失败:", e);
    } finally {
      setMigrating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 语言设置 */}
      <div>
        <label className="text-xs font-medium text-gray-700 block mb-1">
          {t("settings.language.label")}
        </label>
        <select
          value={settings.locale}
          onChange={(e) => setSetting("locale", e.target.value)}
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

      {/* 扩展文件夹路径 */}
      <div>
        <label className="text-xs font-medium text-gray-700 block mb-1">
          {t("settings.general_ext_folder")}
        </label>
        <p className="text-[10px] text-gray-400 mb-2">
          {t("settings.general_ext_desc")}
        </p>
        <div className="flex items-center gap-2">
          <input
            type="text"
            readOnly
            value={displayPath}
            placeholder={t("settings.general_fetching_path")}
            className="flex-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-gray-50
                       focus:outline-none"
          />
          <button
            onClick={handleSelectFolder}
            disabled={migrating}
            className="shrink-0 text-xs px-3 py-1.5 bg-indigo-50 text-indigo-600
                       border border-indigo-200 rounded-lg hover:bg-indigo-100
                       disabled:opacity-50 transition-colors"
          >
              {migrating ? t("settings.general_migrating") : t("settings.general_select_folder")}
          </button>
        </div>
        {!settings["general.extensions_path"] && defaultPath && (
          <p className="mt-1 text-[10px] text-gray-400">
            {t("settings.general_default_path")}{defaultPath}
          </p>
        )}
        {settings["general.extensions_path"] && (
          <button
            onClick={() => setSetting("general.extensions_path", "")}
            className="mt-1 text-[10px] text-gray-400 hover:text-red-500 transition-colors"
          >
            {t("settings.general_reset_path")}
          </button>
        )}
      </div>
    </div>
  );
}
