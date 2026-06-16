import { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useSettingsStore } from "../../stores/settingsStore";
import { cloneVoice, generateVoice, previewVoice } from "../../services/voice";
import { playAudio } from "../../services/audio";

function VoicePresetCard({
  voiceId,
  emoji,
  label,
  active,
  onSelect,
}: {
  voiceId: string;
  emoji: string;
  label: string;
  active: boolean;
  onSelect: () => void;
}) {
  const [previewing, setPreviewing] = useState(false);
  const { t } = useTranslation();

  const handlePreview = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (previewing) return;
    setPreviewing(true);
    const audio = await previewVoice(voiceId);
    if (audio) {
      await playAudio(audio, () => {}, () => setPreviewing(false));
    } else {
      setPreviewing(false);
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`group p-2 rounded-lg text-xs text-center transition-all relative cursor-pointer ${
        active
          ? "bg-primary-50 border border-primary-300 text-primary-700"
          : "bg-gray-50 border border-gray-100 text-gray-600 hover:bg-gray-100"
      }`}
    >
      <div className="text-base mb-0.5">{emoji}</div>
      {label}
      <button
        onClick={handlePreview}
        disabled={previewing}
        className="absolute top-1 right-1 w-5 h-5 flex items-center justify-center
                   rounded-full bg-white/80 hover:bg-white shadow-sm
                   text-xs opacity-0 group-hover:opacity-100 transition-opacity
                   disabled:opacity-50"
        title={t("settings.voice_preview")}
      >
        {previewing ? "⏳" : "▶"}
      </button>
    </div>
  );
}

export function VoiceConfig() {
  const { t } = useTranslation();
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [description, setDescription] = useState("");
  const [generating, setGenerating] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [generated, setGenerated] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 预设音线
  const PRESETS = [
    { id: "sweet_female", emoji: "🌸", nameKey: "voice_preset_sweet_female" },
    { id: "cute_female", emoji: "🐱", nameKey: "voice_preset_cute_female" },
    { id: "cool_female", emoji: "🌊", nameKey: "voice_preset_cool_female" },
    { id: "gentle_male", emoji: "🌿", nameKey: "voice_preset_gentle_male" },
    { id: "energetic_male", emoji: "⚡", nameKey: "voice_preset_energetic_male" },
    { id: "neutral", emoji: "🎭", nameKey: "voice_preset_neutral" },
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
        <span className="text-xs text-gray-700">{t("settings.voice_enable")}</span>
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
          {/* TTS 引擎选择 */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">{t("settings.voice_tts_engine")}</label>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { id: "edge", name: "Edge TTS", descKey: "voice_engine_free" },
                { id: "xiaomi", name: "MiMo", descKey: "voice_engine_cloud" },
                { id: "openai", name: "OpenAI", descKey: "voice_engine_paid" },
                { id: "kokoro", name: "Kokoro", descKey: "voice_engine_local_beta" },
              ].map((e) => (
                <button
                  key={e.id}
                  onClick={() => setSetting("voice.provider", e.id)}
                  className={`p-2 rounded-lg text-xs text-left transition-all ${
                    settings["voice.provider"] === e.id
                      ? "bg-primary-50 border border-primary-300 text-primary-700"
                      : "bg-gray-50 border border-gray-100 text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <div className="font-medium">{e.name}</div>
                  <div className="text-[10px] opacity-60">{t(`settings.${e.descKey}`)}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 预设音线选择 */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">{t("settings.voice_presets")}</label>
            <div className="grid grid-cols-3 gap-1.5">
              {PRESETS.map((v) => (
                <VoicePresetCard
                  key={v.id}
                  voiceId={v.id}
                  emoji={v.emoji}
                  label={t(`settings.${v.nameKey}`)}
                  active={settings["voice.preset_id"] === v.id}
                  onSelect={() => setSetting("voice.preset_id", v.id)}
                />
              ))}
            </div>
          </div>

          {/* 上传音频克隆 */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">{t("settings.voice_voice_clone")}</label>
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
              {cloning ? t("settings.voice_clone_loading") : t("settings.voice_clone_button")}
            </button>
          </div>

          {/* AI 生成音线 */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">{t("settings.voice_ai_generate")}</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t("settings.voice_ai_placeholder")}
                className="flex-1 text-xs px-2 py-1.5 border border-gray-200 rounded-lg bg-white/80
                           focus:outline-none focus:border-primary-400"
              />
              <button
                onClick={handleGenerate}
                disabled={generating || !description.trim()}
                className="px-3 py-1.5 text-xs text-white bg-primary-500 rounded-lg
                           hover:bg-primary-600 disabled:opacity-50 transition-colors"
              >
                {generating ? t("settings.voice_generating") : t("settings.voice_generate")}
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
                    {t("settings.voice_preview")}
                  </button>
                  <button
                    onClick={applyGenerated}
                    className="text-xs text-green-600 hover:underline"
                  >
                    {t("settings.voice_apply")}
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
                <label className="text-xs text-gray-500">{t("settings.voice_speed")}</label>
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
                <label className="text-xs text-gray-500">{t("settings.voice_pitch")}</label>
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
