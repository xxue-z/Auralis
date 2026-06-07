import { useSettingsStore } from "../../stores/settingsStore";

const PRESET_COLORS = [
  { name: "蓝色", value: "#0ea5e9" },
  { name: "紫色", value: "#a855f7" },
  { name: "绿色", value: "#22c55e" },
  { name: "粉色", value: "#ec4899" },
  { name: "橙色", value: "#f97316" },
  { name: "红色", value: "#ef4444" },
];

export function ThemeConfig() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);

  return (
    <div className="space-y-3">
      {/* 主题色 */}
      <div>
        <label className="text-xs text-gray-500">聊天主题色</label>
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
              title={c.name}
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

      {/* 透明度 */}
      <div>
        <div className="flex justify-between items-center">
          <label className="text-xs text-gray-500">聊天透明度</label>
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

      {/* 精灵大小 */}
      <div>
        <div className="flex justify-between items-center">
          <label className="text-xs text-gray-500">精灵大小</label>
          <span className="text-xs text-gray-400">
            {settings["appearance.sprite_size"] || 96}px
          </span>
        </div>
        <input
          type="range"
          min="64"
          max="200"
          step="8"
          value={settings["appearance.sprite_size"] || 96}
          onChange={(e) => setSetting("appearance.sprite_size", parseInt(e.target.value))}
          className="w-full mt-1 accent-primary-500"
        />
      </div>
    </div>
  );
}
