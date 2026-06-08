import { useState, useRef } from "react";
import { cloneVoice, generateVoice, previewVoice } from "../../services/voice";
import { playAudio, stopAudio } from "../../services/audio";
import type { OnboardingData } from "./Wizard";

let _previewSeq = 0; // 全局递增序列号，用于丢弃过期请求

interface Props {
  data: OnboardingData;
  onChange: (partial: Partial<OnboardingData>) => void;
}

const VOICES = [
  { id: "sweet_female", emoji: "🌸", name: "甜美女声", nameEn: "Sweet", desc: "温柔甜美" },
  { id: "cute_female", emoji: "🐱", name: "软萌女声", nameEn: "Cute", desc: "可爱软萌" },
  { id: "cool_female", emoji: "🌊", name: "清冷女声", nameEn: "Cool", desc: "冷静优雅" },
  { id: "gentle_male", emoji: "🌿", name: "温柔男声", nameEn: "Gentle", desc: "温和稳重" },
  { id: "energetic_male", emoji: "⚡", name: "活泼男声", nameEn: "Energetic", desc: "充满活力" },
  { id: "neutral", emoji: "🎭", name: "中性音", nameEn: "Neutral", desc: "平和中性" },
];

export function StepVoice({ data, onChange }: Props) {
  const [playing, setPlaying] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [generating, setGenerating] = useState(false);
  const [cloning, setCloning] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isZh = data.locale === "zh-CN";

  const handlePreview = async (voiceId: string) => {
    setPreviewError(null);

    // 如果正在播放同一个音线，停止播放
    if (playing === voiceId) {
      stopAudio();
      setPlaying(null);
      return;
    }

    // 停止之前的播放
    if (playing) {
      stopAudio();
      setPlaying(null);
    }

    // 递增序列号，丢弃过期请求的结果
    const seq = ++_previewSeq;
    setPreviewing(voiceId);
    try {
      const audio = await previewVoice(voiceId);
      // 已被更新的请求覆盖，丢弃结果
      if (seq !== _previewSeq) return;
      setPreviewing(null);
      if (audio) {
        setPlaying(voiceId);
        await playAudio(audio, undefined, () => setPlaying(null));
      } else {
        setPreviewError(isZh ? "试听失败，请确认 Agent 已启动" : "Preview failed. Is the Agent running?");
        setTimeout(() => setPreviewError(null), 4000);
      }
    } catch {
      if (seq !== _previewSeq) return;
      setPreviewing(null);
      setPlaying(null);
    }
  };

  // AI 生成音线
  const handleGenerate = async () => {
    if (!description.trim()) return;
    setGenerating(true);
    const result = await generateVoice(description);
    setGenerating(false);
    if (result) {
      onChange({ voiceId: result.voice_id });
      if (result.preview_audio) {
        playAudio(result.preview_audio);
      }
    }
  };

  // 上传音频克隆
  const handleClone = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCloning(true);
    const result = await cloneVoice(file);
    setCloning(false);
    if (result) {
      onChange({ voiceId: result.voice_id });
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-bold text-gray-800">
          {isZh ? "选择音线" : "Choose a Voice"}
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          {isZh ? "选择预设音线，或上传音频/描述来创建专属音色" : "Pick a preset, or upload audio to clone"}
        </p>
      </div>

      {/* 预设音线 */}
      <div className="grid grid-cols-2 gap-2">
        {VOICES.map((voice) => (
          <div
            key={voice.id}
            onClick={() => onChange({ voiceId: voice.id })}
            className={`p-3 rounded-xl border-2 text-left transition-all cursor-pointer ${
              data.voiceId === voice.id
                ? "border-primary-500 bg-primary-50"
                : "border-gray-100 hover:border-gray-200"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{voice.emoji}</span>
              <span className="text-sm font-medium text-gray-800">
                {isZh ? voice.name : voice.nameEn}
              </span>
            </div>
            <div className="text-xs text-gray-400">{voice.desc}</div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePreview(voice.id);
              }}
              disabled={previewing !== null && previewing !== voice.id}
              className="mt-2 text-xs text-primary-500 hover:text-primary-600 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {playing === voice.id
                ? "🔊 播放中..."
                : previewing === voice.id
                ? "⏳ 生成中..."
                : "▶ 试听"}
            </button>
          </div>
        ))}
      </div>

      {/* 试听错误提示 */}
      {previewError && (
        <div className="text-xs text-center py-1.5 px-3 bg-amber-50 text-amber-600 rounded-lg border border-amber-200">
          ⚠️ {previewError}
        </div>
      )}

      {/* 上传音频克隆 */}
      <div className="border-t border-gray-100 pt-3">
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={handleClone}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={cloning}
          className="w-full py-2 text-xs text-gray-600 bg-gray-50 border border-gray-200
                     rounded-lg hover:bg-gray-100 disabled:opacity-50 transition-colors"
        >
          {cloning ? "克隆中..." : "📤 上传音频克隆音色（3-10秒）"}
        </button>
      </div>

      {/* AI 生成音线 */}
      <div>
        <div className="flex gap-2">
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={isZh ? "描述想要的音色，如：低沉沙哑的男声" : "Describe your voice, e.g. deep raspy male"}
            className="flex-1 text-xs px-2 py-1.5 border border-gray-200 rounded-lg bg-white/80
                       focus:outline-none focus:border-primary-400"
          />
          <button
            onClick={handleGenerate}
            disabled={generating || !description.trim()}
            className="px-3 py-1.5 text-xs text-white bg-primary-500 rounded-lg
                       hover:bg-primary-600 disabled:opacity-50 transition-colors"
          >
            {generating ? "生成中..." : "AI 生成"}
          </button>
        </div>
      </div>
    </div>
  );
}
