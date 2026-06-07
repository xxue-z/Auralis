import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import enUS from "./locales/en-US.json";
import zhCN from "./locales/zh-CN.json";

// 从 auralis-settings 中读取 locale（与 settingsStore 统一）
// 默认英文，用户手动切换后才改变
function getInitialLocale(): string {
  try {
    const saved = localStorage.getItem("auralis-settings");
    if (saved) {
      const settings = JSON.parse(saved);
      if (settings.locale) return settings.locale;
    }
  } catch {}
  return "en-US"; // 默认英文
}

i18n.use(initReactI18next).init({
  resources: {
    "en-US": { translation: enUS },
    "zh-CN": { translation: zhCN },
  },
  lng: getInitialLocale(),
  fallbackLng: "en-US",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
