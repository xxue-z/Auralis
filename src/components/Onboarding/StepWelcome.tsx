import type { OnboardingData } from "./Wizard";

interface Props {
  data: OnboardingData;
  onChange: (partial: Partial<OnboardingData>) => void;
}

const LANGUAGES = [
  { code: "en-US", name: "English", flag: "🇺🇸" },
  { code: "zh-CN", name: "中文", flag: "🇨🇳" },
];

export function StepWelcome({ data, onChange }: Props) {
  return (
    <div className="text-center space-y-6">
      {/* 精灵预览 */}
      <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-primary-400 to-purple-400
                      flex items-center justify-center shadow-lg">
        <span className="text-4xl">🧚</span>
      </div>

      {/* 欢迎文字 */}
      <div>
        <h1 className="text-xl font-bold text-gray-800">
          {data.locale === "zh-CN" ? "欢迎使用 Auralis！" : "Welcome to Auralis!"}
        </h1>
        <p className="text-sm text-gray-500 mt-2">
          {data.locale === "zh-CN"
            ? "我是你的桌面精灵助手，让我来帮你配置吧。"
            : "I'm your desktop fairy assistant. Let's set things up!"}
        </p>
      </div>

      {/* 语言选择 */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400">
          {data.locale === "zh-CN" ? "选择语言" : "Choose your language"}
        </p>
        <div className="flex gap-3 justify-center">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => onChange({ locale: lang.code })}
              className={`px-6 py-3 rounded-xl border-2 text-sm font-medium transition-all ${
                data.locale === lang.code
                  ? "border-primary-500 bg-primary-50 text-primary-700"
                  : "border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              <span className="text-lg mr-1">{lang.flag}</span>
              {lang.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
