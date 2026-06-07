import type { OnboardingData } from "./Wizard";

interface Props {
  data: OnboardingData;
  onChange: (partial: Partial<OnboardingData>) => void;
}

const STYLES = [
  { id: "neko", emoji: "🐱", name: "猫娘", nameEn: "Neko", desc: "温柔可爱", color: "#ec4899" },
  { id: "kitsune", emoji: "🦊", name: "狐仙", nameEn: "Kitsune", desc: "古灵精怪", color: "#f97316" },
  { id: "fairy", emoji: "🧚", name: "精灵", nameEn: "Fairy", desc: "优雅空灵", color: "#a855f7" },
  { id: "android", emoji: "🤖", name: "机器人", nameEn: "Android", desc: "冷静理性", color: "#3b82f6" },
  { id: "blossom", emoji: "🌸", name: "花灵", nameEn: "Blossom", desc: "甜美温暖", color: "#ec4899" },
];

export function StepStyle({ data, onChange }: Props) {
  const isZh = data.locale === "zh-CN";

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-bold text-gray-800">
          {isZh ? "选择精灵风格" : "Choose a Style"}
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          {isZh ? "每种风格有独特的外观和音线" : "Each style has a unique look and voice"}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {STYLES.map((style) => (
          <button
            key={style.id}
            onClick={() => onChange({ spriteStyle: style.id, spriteColor: style.color })}
            className={`flex items-center gap-3 p-3 rounded-xl border-2 text-left transition-all ${
              data.spriteStyle === style.id
                ? "border-primary-500 bg-primary-50"
                : "border-gray-100 hover:border-gray-200"
            }`}
          >
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
              style={{ background: `${style.color}20` }}
            >
              {style.emoji}
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-800">
                {isZh ? style.name : style.nameEn}
              </div>
              <div className="text-xs text-gray-400">{style.desc}</div>
            </div>
            {data.spriteStyle === style.id && (
              <div className="text-primary-500 text-lg">✓</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
