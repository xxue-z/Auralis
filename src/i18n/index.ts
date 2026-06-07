import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import enUS from "./locales/en-US.json";
import zhCN from "./locales/zh-CN.json";

const savedLang = localStorage.getItem("auralis-locale");
const browserLang = navigator.language;
const defaultLang = savedLang || (browserLang.startsWith("zh") ? "zh-CN" : "en-US");

i18n.use(initReactI18next).init({
  resources: {
    "en-US": { translation: enUS },
    "zh-CN": { translation: zhCN },
  },
  lng: defaultLang,
  fallbackLng: "en-US",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
