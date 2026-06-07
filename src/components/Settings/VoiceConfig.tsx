import { useState, useRef } from "react";
import { useSettingsStore } from "../../stores/settingsStore";
import { cloneVoice, generateVoice } from "../../services/voice";
import { playAudio } from "../../services/audio";

export function VoiceConfig() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [description, setDescription] = useState("");
  const [generating, setGenerating] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [generated, setGenerated] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 预设音线
  const PRESETS = [
    { id: "sweet_female", emoji: "🌸", name: "甜美女声" },
    { id: "cute_female", emoji: "🐱", name: "软萌女声" },
    { id: "cool_female", emoji: "🌊", name: "清冷女声" },
    { id: "gentle_male", emoji: "🌿", name: "温柔男声" },
    { id: "energetic_male", emoji: "⚡", name: "活泼男声" },
    { id: "neutral", emoji: "🎭", name: "中性音" },
  ];

  // AI 生成音线
  const handleGenerate = async () => {
    if (!description.trim()) return;
    setGenerating(true);
    const result = await generateVoice(description);
    setGenerating(false);
    if (result) {
      setGenerated(result);
    }
  };

  // 应用生成的音线
  const applyGenerated = () => {
    if (generated) {
      setSetting("voice.preset_id", generated.voice_id);
      setGenerated(null);
      setDescription("");
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
      setSetting("voice.preset_id", result.voice_id);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-4">
      {/* 启用语音 */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-700">启用语音回答</span>
        <button
          onClick={() => setSetting("voice.enabled", !settings["voice.enabled"])}
          className={`w-10 h-5 rounded-full transition-colors ${
            settings["voice.enabled"] ? "bg-primary-500" : "bg-gray-300"
          }`}
        >
          <div
            className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${
              settings["voice.enabled"] ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {settings["voice.enabled"] && (
        <>
          {/* 预设音线选择 */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">预设音线</label>
            <div className="grid grid-cols-3 gap-1.5">
              {PRESETS.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSetting("voice.preset_id", v.id)}
                  className={`p-2 rounded-lg text-xs text-center transition-all ${
                    settings["voice.preset_id"] === v.id
                      ? "bg-primary-50 border border-primary-300 text-primary-700"
                      : "bg-gray-50 border border-gray-100 text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <div className="text-base mb-0.5">{v.emoji}</div>
                  {v.name}
                </button>
              ))}
            </div>
          </div>

          {/* 上传音频克隆 */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">声音克隆</label>
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
            <label className="text-xs text-gray-500 block mb-2">AI 生成音线</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="描述想要的音色，如：低沉沙哑的男声"
                className="flex-1 text-xs px-2 py-1.5 border border-gray-200 rounded-lg bg-white/80
                           focus:outline-none focus:border-primary-400"
              />
              <button
                onClick={handleGenerate}
                disabled={generating || !description.trim()}
                className="px-3 py-1.5 text-xs text-white bg-primary-500 rounded-lg
                           hover:bg-primary-600 disabled:opacity-50 transition-colors"
              >
                {generating ? "生成中..." : "生成"}
              </button>
            </div>
          </div>

          {/* 生成结果 */}
          {generated && (
            <div className="p-2 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs text-green-700">✅ {generated.name}</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => playAudio(generated.preview_audio)}
                    className="text-xs text-primary-500 hover:underline"
                  >
                    试听
                  </button>
                  <button
                    onClick={applyGenerated}
                    className="text-xs text-green-600 hover:underline"
                  >
                    应用
                  </button>
                </div>
              </div>
              <p className="text-xs text-green-600 mt-1">{generated.description}</p>
            </div>
          )}

          {/* 语速/音调 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="flex justify-between items-center">
                <label className="text-xs text-gray-500">语速</label>
                <span className="text-xs text-gray-400">{settings["voice.speed"]}</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings["voice.speed"]}
                onChange={(e) => setSetting("voice.speed", parseFloat(e.target.value))}
                className="w-full mt-1 accent-primary-500"
              />
            </div>
            <div>
              <div className="flex justify-between items-center">
                <label className="text-xs text-gray-500">音调</label>
                <span className="text-xs text-gray-400">{settings["voice.pitch"]}</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings["voice.pitch"]}
                onChange={(e) => setSetting("voice.pitch", parseFloat(e.target.value))}
                className="w-full mt-1 accent-primary-500"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
