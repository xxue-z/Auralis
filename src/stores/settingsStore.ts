import { create } from "zustand";
import i18n from "../i18n";

// 所有设置项的默认值
const DEFAULT_SETTINGS: Record<string, any> = {
  // 语言
  locale: "en-US",
  // 人格
  "persona.proactive": 0.3,
  "persona.humor": 0.5,
  "persona.verbosity": 0.4,
  "persona.precision": 0.8,
  // 云端模型
  "model.cloud.enabled": true,
  "model.cloud.vendor": "OpenAI",
  "model.cloud.base_url": "https://api.openai.com/v1",
  "model.cloud.api_protocol": "openai",
  "model.cloud.api_key": "",
  "model.cloud.model_id": "gpt-4o",
  "model.cloud.custom_vendors": "[]",
  // 本地模型（Ollama）
  "model.local.enabled": false,
  "model.local.base_url": "http://localhost:11434/v1",
  "model.local.model_id": "qwen2.5:1.5b",
  // 通用
  "model.auto_switch": true,
  // 安全
  "security.confirm_destructive": true,
  "security.audit_log": true,
  // 外观
  "appearance.theme": "system",
  "appearance.chat_color": "#0ea5e9",
  "appearance.chat_opacity": 0.9,
  "appearance.sprite_size": 96,
  "appearance.sprite_style": "",
  // 引导
  "onboarding.complete": false,
  // 语音
  "voice.enabled": false,
  "voice.preset_id": "sweet_female",
  "voice.provider": "edge-tts",
  "voice.speed": 1.0,
  "voice.pitch": 1.0,
  "voice.custom_clone_id": "",
};

// 从 localStorage 加载已保存的设置
function loadSettings(): Record<string, any> {
  try {
    const saved = localStorage.getItem("auralis-settings");
    if (saved) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
    }
  } catch {}
  return { ...DEFAULT_SETTINGS };
}

interface SettingsState {
  settings: Record<string, any>;
  getSetting: (key: string) => any;
  setSetting: (key: string, value: any) => void;
  setSettings: (changes: Array<{ key: string; value: any }>) => void;
  getAllSettings: () => Record<string, any>;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: loadSettings(),

  getSetting: (key: string) => {
    return get().settings[key];
  },

  setSetting: (key: string, value: any) => {
    const newSettings = { ...get().settings, [key]: value };
    localStorage.setItem("auralis-settings", JSON.stringify(newSettings));
    set({ settings: newSettings });

    // 特殊处理：locale 变更同步到 i18n
    if (key === "locale") {
      i18n.changeLanguage(value);
    }
  },

  setSettings: (changes: Array<{ key: string; value: any }>) => {
    const newSettings = { ...get().settings };
    for (const { key, value } of changes) {
      newSettings[key] = value;
      if (key === "locale") {
        i18n.changeLanguage(value);
      }
    }
    localStorage.setItem("auralis-settings", JSON.stringify(newSettings));
    set({ settings: newSettings });
  },

  getAllSettings: () => {
    return { ...get().settings };
  },
}));
