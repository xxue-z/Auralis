import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { emit } from "@tauri-apps/api/event";
import { useSettingsStore } from "../../stores/settingsStore";
import { ModelSelector } from "../Character/ModelSelector";

const PRESET_COLORS = [
  { nameKey: "theme_color_blue", value: "#0ea5e9" },
  { nameKey: "theme_color_purple", value: "#a855f7" },
  { nameKey: "theme_color_green", value: "#22c55e" },
  { nameKey: "theme_color_pink", value: "#ec4899" },
  { nameKey: "theme_color_orange", value: "#f97316" },
  { nameKey: "theme_color_red", value: "#ef4444" },
];

export function ThemeConfig() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"live2d" | "chat">("live2d");
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const guideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const emitClickGuide = () => {
    emit("click-zone-preview", { show: true }).catch(() => {});
    if (guideTimerRef.current) clearTimeout(guideTimerRef.current);
    guideTimerRef.current = setTimeout(() => {
      emit("click-zone-preview", { show: false }).catch(() => {});
    }, 1500);
  };

  const modelId = settings["appearance.model_id"] || "svg_fallback";

  const screenMax = useMemo(() => {
    const h = window.screen.availHeight;
    const w = window.screen.availWidth;
    return Math.max(64, Math.min(h, w));
  }, []);

  // Per-model settings (fallback chain: per-model → global → default)
  const spriteSize = settings[`model:${modelId}:sprite_size`] ?? settings["appearance.sprite_size"] ?? 96;
  const spriteOpacity = settings[`model:${modelId}:sprite_opacity`] ?? settings["appearance.sprite_opacity"] ?? 1;
  const windowRatio = settings[`model:${modelId}:window_ratio`] ?? 1.0;

  const spritePct = Math.round((spriteSize / screenMax) * 100);

  const handleSpritePct = (pct: number) => {
    const px = Math.round((pct / 100) * screenMax);
    setSetting(`model:${modelId}:sprite_size`, Math.max(32, px));
  };

  const tabLabel = (key: "live2d" | "chat"): string => {
    const labels: Record<string, string> = {
      live2d: t("settings.tab_live2d"),
      chat: t("settings.tab_chat"),
    };
    return labels[key] || key;
  };

  return (
    <div className="space-y-3">
      {/* Top Tabs */}
      <div className="flex gap-1 border-b border-gray-200 pb-2">
        {(["live2d", "chat"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
              tab === k
                ? "bg-indigo-50 text-indigo-700 border-b-2 border-indigo-500"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tabLabel(k)}
          </button>
        ))}
      </div>

      {tab === "live2d" && (
        <div className="space-y-4">
          <ModelSelector />

          <div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-gray-500">{t("settings.model_window_ratio")}</label>
              <span className="text-xs text-gray-400">
                {Math.round(windowRatio * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.2"
              max="2.5"
              step="0.05"
              value={windowRatio}
              onChange={(e) => setSetting(`model:${modelId}:window_ratio`, parseFloat(e.target.value))}
              className="w-full mt-1 accent-primary-500"
            />
          </div>

          <div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-gray-500">{t("settings.model_size")}</label>
              <span className="text-xs text-gray-400">{spritePct}% ({spriteSize}px)</span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              step="1"
              value={spritePct}
              onChange={(e) => handleSpritePct(parseInt(e.target.value))}
              className="w-full mt-1 accent-primary-500"
            />
          </div>

          <div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-gray-500">{t("settings.model_opacity")}</label>
              <span className="text-xs text-gray-400">{Math.round(spriteOpacity * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1"
              step="0.05"
              value={spriteOpacity}
              onChange={(e) => setSetting(`model:${modelId}:sprite_opacity`, parseFloat(e.target.value))}
              className="w-full mt-1 accent-primary-500"
            />
          </div>

          <div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-gray-500">{t("settings.click_zone_w")}</label>
              <span className="text-xs text-gray-400">{settings["appearance.click_zone_w"] ?? 60}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={settings["appearance.click_zone_w"] ?? 60}
              onChange={(e) => {
                setSetting("appearance.click_zone_w", parseInt(e.target.value));
                emitClickGuide();
              }}
              className="w-full mt-1 accent-primary-500"
            />
          </div>
          <div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-gray-500">{t("settings.click_zone_h")}</label>
              <span className="text-xs text-gray-400">{settings["appearance.click_zone_h"] ?? 80}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={settings["appearance.click_zone_h"] ?? 80}
              onChange={(e) => {
                setSetting("appearance.click_zone_h", parseInt(e.target.value));
                emitClickGuide();
              }}
              className="w-full mt-1 accent-primary-500"
            />
          </div>
        </div>
      )}

      {tab === "chat" && (
        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-500">{t("settings.chat_theme_color")}</label>
            <div className="flex gap-2 mt-1.5 flex-wrap">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c.value}
                  onClick={() => setSetting("appearance.chat_color", c.value)}
                  className={`w-7 h-7 rounded-full border-2 transition-all ${
                    settings["appearance.chat_color"] === c.value
                      ? "border-gray-800 scale-110"
                      : "border-transparent"
                  }`}
                  style={{ background: c.value }}
                  title={t(`settings.${c.nameKey}`)}
                />
              ))}
              <input
                type="color"
                value={settings["appearance.chat_color"] || "#0ea5e9"}
                onChange={(e) => setSetting("appearance.chat_color", e.target.value)}
                className="w-7 h-7 rounded cursor-pointer border-0"
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-gray-500">{t("settings.chat_opacity")}</label>
              <span className="text-xs text-gray-400">
                {((settings["appearance.chat_opacity"] || 0.9) * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.3"
              max="1"
              step="0.05"
              value={settings["appearance.chat_opacity"] || 0.9}
              onChange={(e) => setSetting("appearance.chat_opacity", parseFloat(e.target.value))}
              className="w-full mt-1 accent-primary-500"
            />
          </div>
        </div>
      )}
    </div>
  );
}
