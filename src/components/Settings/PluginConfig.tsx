import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { useSettingsStore } from "../../stores/settingsStore";

interface PluginInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  source: string;
  added_at: string;
  enabled: boolean;
}

function PowerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v10" />
      <path d="M18.4 6.6a9 9 0 1 1-12.77.04" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18" />
      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    </svg>
  );
}

async function resolvePluginsDir(extensionsPath: string): Promise<string> {
  if (extensionsPath) return extensionsPath;
  const defaultDir = await invoke<string>("get_app_data_dir");
  return defaultDir;
}

export function PluginConfig() {
  const { t } = useTranslation();
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [search, setSearch] = useState("");
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const extensionsPath = settings["general.extensions_path"] || "";

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const base = await resolvePluginsDir(extensionsPath);

      const [system, user] = await Promise.all([
        invoke<PluginInfo[]>("list_system_plugins").catch(() => [] as PluginInfo[]),
        invoke<PluginInfo[]>("list_user_plugins", { extensionsPath: base }).catch(() => [] as PluginInfo[]),
      ]);

      const raw = settings["plugins_state"] || "{}";
      const state: Record<string, boolean> =
        typeof raw === "string" ? JSON.parse(raw) : raw;

      setPlugins(
        [...system, ...user].map((p) => ({
          ...p,
          enabled: state[p.id] ?? true,
        }))
      );
    } catch (e) {
      console.error("加载插件列表失败:", e);
      setError(t("settings.plugin_empty"));
    } finally {
      setLoading(false);
    }
  }, [extensionsPath, settings]);

  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const saveState = (list: PluginInfo[]) => {
    const state: Record<string, boolean> = {};
    for (const p of list) state[p.id] = p.enabled;
    setSetting("plugins_state", JSON.stringify(state));
  };

  const filtered = useMemo(
    () =>
      plugins.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.description.toLowerCase().includes(search.toLowerCase())
      ),
    [plugins, search]
  );

  const togglePlugin = (id: string) => {
    const next = plugins.map((p) =>
      p.id === id ? { ...p, enabled: !p.enabled } : p
    );
    setPlugins(next);
    saveState(next);
  };

  const deletePlugin = async (id: string) => {
    try {
      const base = await resolvePluginsDir(extensionsPath);
      await invoke("delete_user_plugin", { pluginId: id, extensionsPath: base });
      setPlugins((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      console.error(t("settings.plugin_delete"), e);
    }
  };

  const handleImportFolder = async () => {
    const selected = await open({ multiple: false, directory: true, title: t("settings.plugin_select_folder_title") });
    if (!selected) return;
    try {
      const base = await resolvePluginsDir(extensionsPath);
      const info = await invoke<PluginInfo>("import_plugin", {
        sourcePath: selected,
        extensionsPath: base,
      });
      setPlugins((prev) => [...prev, { ...info, enabled: true }]);
    } catch (e: any) {
      alert(`${t("settings.plugin_import_failed")}: ${e}`);
    }
  };

  const handleImportZip = async () => {
    const selected = await open({ multiple: false, filters: [{ name: "ZIP", extensions: ["zip"] }], title: t("settings.plugin_select_zip_title") });
    if (!selected) return;
    try {
      const base = await resolvePluginsDir(extensionsPath);
      const info = await invoke<PluginInfo>("import_plugin_zip", {
        zipPath: selected,
        extensionsPath: base,
      });
      setPlugins((prev) => [...prev, { ...info, enabled: true }]);
    } catch (e: any) {
      alert(`${t("settings.plugin_import_failed")}: ${e}`);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("settings.search_plugins")}
          className="w-1/3 text-xs px-3 py-1.5 border border-gray-200 rounded-lg
                     bg-white/80 focus:outline-none focus:border-primary-400"
        />
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-600
                       border border-indigo-200 rounded-lg hover:bg-indigo-100
                       transition-colors flex items-center gap-1"
          >
            {t("settings.plugin_import")}
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-10 overflow-hidden">
              <button
                onClick={() => { setMenuOpen(false); handleImportFolder(); }}
                className="w-full text-left text-xs px-3 py-2 hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                </svg>
                {t("settings.plugin_import_folder")}
              </button>
              <button
                onClick={() => { setMenuOpen(false); handleImportZip(); }}
                className="w-full text-left text-xs px-3 py-2 hover:bg-gray-50 transition-colors flex items-center gap-2 border-t border-gray-100"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
                {t("settings.plugin_import_zip")}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden">
        {loading && (
          <div className="text-center py-8 text-xs text-gray-400">{t("settings.plugin_loading")}</div>
        )}
        {error && (
          <div className="text-center py-8 text-xs text-red-400">{error}</div>
        )}
        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-8 text-xs text-gray-400">{t("settings.plugin_empty")}</div>
        )}

        {!loading && filtered.map((plugin) => (
          <div
            key={plugin.id}
            className={`flex items-center gap-3 px-3 py-2.5 border-b border-gray-100 text-xs transition-colors ${
              plugin.source === "system"
                ? "bg-blue-50/40 hover:bg-blue-50/70"
                : "hover:bg-gray-50/50"
            }`}
          >
            <div className="w-[22%] shrink-0 font-medium text-gray-800 truncate">
              {plugin.name}
            </div>
            <div className="flex-1 text-gray-500 truncate min-w-0" title={plugin.description}>
              {plugin.description || "-"}
            </div>
            <div className="w-[10%] shrink-0 text-gray-400 text-[11px]">
              v{plugin.version}
            </div>
            <div className="flex items-center justify-end gap-1 w-[18%] shrink-0">
              <button
                onClick={() => togglePlugin(plugin.id)}
                className={`w-7 h-7 flex items-center justify-center rounded-md transition-colors ${
                  plugin.enabled
                    ? "text-green-500 hover:bg-green-50"
                    : "text-gray-400 hover:bg-gray-100"
                }`}
                title={plugin.enabled ? t("settings.plugin_disable") : t("settings.plugin_enable")}
              >
                <PowerIcon />
              </button>
              {plugin.source !== "system" && (
                <button
                  onClick={() => deletePlugin(plugin.id)}
                  className="w-7 h-7 flex items-center justify-center rounded-md
                             text-red-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                  title={t("settings.plugin_delete")}
                >
                  <TrashIcon />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
