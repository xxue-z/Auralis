import { useState } from "react";
import { useSettingsStore } from "../../stores/settingsStore";
import { StepWelcome } from "./StepWelcome";
import { StepStyle } from "./StepStyle";
import { StepTune } from "./StepTune";
import { StepVoice } from "./StepVoice";

interface OnboardingData {
  locale: string;
  spriteStyle: string;
  spriteColor: string;
  spriteSize: number;
  voiceId: string;
}

const STEPS = ["welcome", "style", "tune", "voice"];

export function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<OnboardingData>({
    locale: "en-US",
    spriteStyle: "",
    spriteColor: "#0ea5e9",
    spriteSize: 96,
    voiceId: "sweet_female",
  });

  const setSetting = useSettingsStore((s) => s.setSetting);

  const updateData = (partial: Partial<OnboardingData>) => {
    setData((prev) => ({ ...prev, ...partial }));
  };

  const handleComplete = async () => {
    // 保存所有设置
    setSetting("locale", data.locale);
    setSetting("appearance.sprite_style", data.spriteStyle);
    setSetting("appearance.chat_color", data.spriteColor);
    setSetting("appearance.sprite_size", data.spriteSize);
    setSetting("voice.preset_id", data.voiceId);
    setSetting("onboarding.complete", true);
    onComplete();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-primary-50 to-purple-50" style={{ WebkitAppRegion: "drag" } as React.CSSProperties}>
      <div className="w-[420px] max-h-[90vh] bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col" style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
        {/* 进度条 */}
        <div className="px-6 pt-6">
          <div className="flex gap-2">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-colors ${
                  i <= step ? "bg-primary-500" : "bg-gray-200"
                }`}
              />
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">
            {step + 1} / {STEPS.length}
          </p>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 0 && <StepWelcome data={data} onChange={updateData} />}
          {step === 1 && <StepStyle data={data} onChange={updateData} />}
          {step === 2 && <StepTune data={data} onChange={updateData} />}
          {step === 3 && <StepVoice data={data} onChange={updateData} />}
        </div>

        {/* 按钮 */}
        <div className="px-6 pb-6 flex gap-3">
          {step > 0 && (
            <button
              onClick={() => setStep(step - 1)}
              className="flex-1 py-2.5 text-sm text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
            >
              上一步
            </button>
          )}
          <button
            onClick={() => {
              if (step < STEPS.length - 1) {
                setStep(step + 1);
              } else {
                handleComplete();
              }
            }}
            disabled={step === 1 && !data.spriteStyle}
            className="flex-1 py-2.5 text-sm font-medium text-white bg-primary-500 rounded-xl
                       hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {step === STEPS.length - 1 ? "开始使用" : "下一步"}
          </button>
        </div>
      </div>
    </div>
  );
}
