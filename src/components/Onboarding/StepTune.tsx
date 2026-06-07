import type { OnboardingData } from "./Wizard";

interface Props {
  data: OnboardingData;
  onChange: (partial: Partial<OnboardingData>) => void;
}

const COLORS = [
  "#ec4899", "#f97316", "#eab308",
  "#22c55e", "#3b82f6", "#a855f7",
];

export function StepTune({ data, onChange }: Props) {
  const isZh = data.locale === "zh-CN";

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-lg font-bold text-gray-800">
          {isZh ? "微调形象" : "Customize Appearance"}
        </h2>
      </div>

      {/* 预览 */}
      <div className="flex justify-center">
        <div
          className="rounded-full flex items-center justify-center shadow-lg transition-all"
          style={{
            width: data.spriteSize,
            height: data.spriteSize,
            background: `linear-gradient(135deg, ${data.spriteColor}, ${data.spriteColor}99)`,
          }}
        >
          <span style={{ fontSize: data.spriteSize * 0.4 }}>🧚</span>
        </div>
      </div>

      {/* 颜色选择 */}
      <div>
        <label className="text-xs text-gray-500 block mb-2">
          {isZh ? "主题色" : "Theme Color"}
        </label>
        <div className="flex gap-2 justify-center">
          {COLORS.map((color) => (
            <button
              key={color}
              onClick={() => onChange({ spriteColor: color })}
              className={`w-8 h-8 rounded-full border-2 transition-all ${
                data.spriteColor === color
                  ? "border-gray-800 scale-110"
                  : "border-transparent"
              }`}
              style={{ background: color }}
            />
          ))}
          <input
            type="color"
            value={data.spriteColor}
            onChange={(e) => onChange({ spriteColor: e.target.value })}
            className="w-8 h-8 rounded cursor-pointer border-0"
          />
        </div>
      </div>

      {/* 大小滑块 */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-xs text-gray-500">
            {isZh ? "精灵大小" : "Sprite Size"}
          </label>
          <span className="text-xs text-gray-400">{data.spriteSize}px</span>
        </div>
        <input
          type="range"
          min="64"
          max="200"
          step="8"
          value={data.spriteSize}
          onChange={(e) => onChange({ spriteSize: parseInt(e.target.value) })}
          className="w-full accent-primary-500"
        />
      </div>
    </div>
  );
}
