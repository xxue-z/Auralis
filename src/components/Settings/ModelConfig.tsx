import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useSettingsStore } from "../../stores/settingsStore";
import { useAgentStore } from "../../stores/agentStore";
import {
  fetchVendors,
  type Vendor,
} from "../../services/vendor-service";
import {
  checkOllamaStatus,
  listOllamaModels,
  type OllamaModel,
} from "../../services/ollama";
import { wsService } from "../../services/websocket";

async function ensureWsConnected(): Promise<boolean> {
  if (wsService.isConnected) return true;
  const url = useAgentStore.getState().url;
  wsService.connect(url);
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 200));
    if (wsService.isConnected) return true;
  }
  return false;
}

type Tab = "cloud" | "local";

export function ModelConfig() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("cloud");

  return (
    <div className="space-y-3">
      <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
        <button
          onClick={() => setTab("cloud")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            tab === "cloud"
              ? "bg-white text-gray-800 shadow-sm"
              : "text-gray-500"
          }`}
        >
          {t("settings.model_tab_cloud")}
        </button>
        <button
          onClick={() => setTab("local")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            tab === "local"
              ? "bg-white text-gray-800 shadow-sm"
              : "text-gray-500"
          }`}
        >
          {t("settings.model_tab_local")}
        </button>
      </div>

      {tab === "cloud" ? <CloudModelConfig /> : <LocalModelConfig />}
    </div>
  );
}

// ============ 云端模型配置 ============

function CloudModelConfig() {
  const { t } = useTranslation();
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);

  const selectedVendor = settings["model.cloud.vendor"] || "OpenAI";
  const currentVendor = vendors.find((v) => v.vendor === selectedVendor);
  const [cloudTest, setCloudTest] = useState<{ testing: boolean; success?: boolean; message?: string }>({ testing: false });
  const cloudTestRef = useRef<((data: any) => void) | null>(null);

  // 加载厂商列表
  useEffect(() => {
    fetchVendors().then((v) => {
      setVendors(v);
      setLoading(false);
    });
  }, []);

  const CUSTOM_VENDOR = t("settings.model_custom");

  // 选择厂商时自动填充
  const handleVendorChange = (vendorName: string) => {
    if (vendorName === CUSTOM_VENDOR) {
      setSetting("model.cloud.vendor", CUSTOM_VENDOR);
      return;
    }

    const vendor = vendors.find((v) => v.vendor === vendorName);
    if (!vendor) return;

    setSetting("model.cloud.vendor", vendorName);
    setSetting("model.cloud.base_url", vendor.base_urls[vendor.supported_modes[0]] || "");
    setSetting("model.cloud.api_protocol", vendor.supported_modes[0]);
    // 选择第一个模型
    if (vendor.models.length > 0) {
      setSetting("model.cloud.model_id", vendor.models[0]);
    }
  };

  const handleCloudTest = async () => {
    setCloudTest({ testing: true });

    const ok = await ensureWsConnected();
    if (!ok) {
      setCloudTest({ testing: false, success: false, message: t("settings.model_test_error") });
      return;
    }

    const id = crypto.randomUUID();

    const handler = (data: any) => {
      if (data.id === id) {
        cloudTestRef.current = null;
        setCloudTest({ testing: false, success: data.success, message: data.message });
      }
    };

    cloudTestRef.current = handler;
    wsService.on("model_test_result", handler);
    wsService.send({ type: "model_test", id, mode: "cloud" });

    setTimeout(() => {
      if (cloudTestRef.current) {
        wsService.off("model_test_result", cloudTestRef.current);
        cloudTestRef.current = null;
        setCloudTest(prev => prev.testing ? { testing: false, success: false, message: t("settings.model_test_timeout") } : prev);
      }
    }, (settings["model.timeout"] || 120) * 1000);
  };

  useEffect(() => {
    return () => {
      if (cloudTestRef.current) {
        wsService.off("model_test_result", cloudTestRef.current);
      }
    };
  }, []);

  if (loading) {
    return <div className="text-xs text-gray-400 text-center py-4">{t("settings.model_loading")}</div>;
  }

  return (
    <div className="space-y-3">
      {/* 启用开关 */}
      <ToggleSetting
        label={t("settings.model_enable_cloud")}
        settingKey="model.cloud.enabled"
      />

      {settings["model.cloud.enabled"] && (
        <>
          {/* 厂商选择 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_vendor")}</label>
            <select
              value={selectedVendor}
              onChange={(e) => handleVendorChange(e.target.value)}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            >
              {vendors.map((v) => (
                  <option key={v.vendor} value={v.vendor}>
                    {v.vendor} — {v.description}
                  </option>
                ))}
                <option value={CUSTOM_VENDOR}>{t("settings.model_custom_option")}</option>
            </select>
          </div>

          {/* API Key */}
          <div>
            <label className="text-xs text-gray-500">
              API Key
              {currentVendor?.key_url && (
                <a
                  href={currentVendor.key_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-1 text-primary-500 hover:underline"
                >
                  {t("settings.model_get_key")}
                </a>
              )}
            </label>
            <input
              type="password"
              value={settings["model.cloud.api_key"] || ""}
              onChange={(e) => setSetting("model.cloud.api_key", e.target.value)}
              placeholder="sk-..."
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            />
          </div>

          {/* Base URL */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_api_base")}</label>
            <input
              type="text"
              value={settings["model.cloud.base_url"] || ""}
              onChange={(e) => setSetting("model.cloud.base_url", e.target.value)}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            />
          </div>

          {/* 协议 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_api_protocol")}</label>
            <select
              value={settings["model.cloud.api_protocol"] || "openai"}
              onChange={(e) => setSetting("model.cloud.api_protocol", e.target.value)}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            >
              <option value="openai">{t("settings.model_openai_compat")}</option>
              <option value="anthropic">{t("settings.model_anthropic")}</option>
            </select>
          </div>

          {/* 模型选择 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_model")}</label>
            <input
              type="text"
              list="cloud-model-list"
              value={settings["model.cloud.model_id"] || ""}
              onChange={(e) => setSetting("model.cloud.model_id", e.target.value)}
              placeholder={t("settings.model_model_placeholder")}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            />
            {currentVendor && currentVendor.models.length > 0 && (
              <datalist id="cloud-model-list">
                {currentVendor.models.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            )}
          </div>

          {/* 超时 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_timeout_sec")}</label>
            <input
              type="number"
              min={5}
              max={600}
              value={settings["model.timeout"] ?? 120}
              onChange={(e) => setSetting("model.timeout", Math.max(5, Math.min(600, Number(e.target.value) || 120)))}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            />
          </div>

          {/* 测试连接 */}
          <div>
            <button
              onClick={handleCloudTest}
              disabled={cloudTest.testing}
              className="w-full mt-1 text-xs px-3 py-1.5 rounded border transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed
                         bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {cloudTest.testing ? t("settings.model_testing") : t("settings.model_test_connection")}
            </button>
            {!cloudTest.testing && cloudTest.message && (
              <div
                className={`mt-1.5 text-xs px-2 py-1 rounded ${
                  cloudTest.success
                    ? "bg-green-50 text-green-700 border border-green-200"
                    : "bg-red-50 text-red-600 border border-red-200"
                }`}
              >
                {cloudTest.success ? "✅ " : "❌ "}{cloudTest.message}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ============ 本地模型配置（Ollama）============

function LocalModelConfig() {
  const { t } = useTranslation();
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [ollamaConnected, setOllamaConnected] = useState<boolean | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);

  const [localTest, setLocalTest] = useState<{ testing: boolean; success?: boolean; message?: string }>({ testing: false });
  const localTestRef = useRef<((data: any) => void) | null>(null);
  const baseUrl = settings["model.local.base_url"] || "http://localhost:11434/v1";

  // 检测 Ollama 状态
  useEffect(() => {
    if (!settings["model.local.enabled"]) return;

    checkOllamaStatus(baseUrl).then((ok) => {
      setOllamaConnected(ok);
      if (ok) {
        listOllamaModels(baseUrl).then(setModels);
      }
    });
  }, [settings["model.local.enabled"], baseUrl]);

  const handleLocalTest = async () => {
    setLocalTest({ testing: true });

    const ok = await ensureWsConnected();
    if (!ok) {
      setLocalTest({ testing: false, success: false, message: t("settings.model_test_error") });
      return;
    }

    const id = crypto.randomUUID();

    const handler = (data: any) => {
      if (data.id === id) {
        localTestRef.current = null;
        setLocalTest({ testing: false, success: data.success, message: data.message });
      }
    };

    localTestRef.current = handler;
    wsService.on("model_test_result", handler);
    wsService.send({ type: "model_test", id, mode: "local" });

    setTimeout(() => {
      if (localTestRef.current) {
        wsService.off("model_test_result", localTestRef.current);
        localTestRef.current = null;
        setLocalTest(prev => prev.testing ? { testing: false, success: false, message: t("settings.model_test_timeout") } : prev);
      }
    }, (settings["model.timeout"] || 120) * 1000);
  };

  useEffect(() => {
    return () => {
      if (localTestRef.current) {
        wsService.off("model_test_result", localTestRef.current);
      }
    };
  }, []);

  return (
    <div className="space-y-3">
      {/* 启用开关 */}
      <ToggleSetting
        label={t("settings.model_enable_local")}
        settingKey="model.local.enabled"
      />

      {/* Ollama 引导 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-gray-600 space-y-1.5">
        <p className="font-medium text-gray-800">
          {t("settings.model_ollama_required")}
        </p>
        <p>{t("settings.model_ollama_desc")}</p>
        <div className="flex gap-3">
          <a
            href="https://ollama.com/download"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-500 hover:underline"
          >
            {t("settings.model_download_ollama")}
          </a>
          <a
            href="https://ollama.com/blog/openai-compatibility"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-500 hover:underline"
          >
            {t("settings.model_config_doc")}
          </a>
        </div>
        <p className="text-gray-400">
          {t("settings.model_after_install")} <code className="bg-gray-100 px-1 rounded">ollama pull qwen2.5:1.5b</code>
        </p>
      </div>

      {settings["model.local.enabled"] && (
        <>
          {/* 连接状态 */}
          <div className="flex items-center gap-2 text-xs">
            <span>{t("settings.model_status")}</span>
            {ollamaConnected === null ? (
              <span className="text-gray-400">{t("settings.model_checking")}</span>
            ) : ollamaConnected ? (
              <span className="text-green-600">{t("settings.model_connected")}</span>
            ) : (
              <span className="text-red-500">{t("settings.model_disconnected")}</span>
            )}
          </div>

          {/* API 地址 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_ollama_url")}</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setSetting("model.local.base_url", e.target.value)}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            />
          </div>

          {/* 模型选择 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_model")}</label>
            {models.length > 0 ? (
              <select
                value={settings["model.local.model_id"] || ""}
                onChange={(e) => setSetting("model.local.model_id", e.target.value)}
                className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                           focus:outline-none focus:border-primary-400"
              >
                {models.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.name} ({(m.size / 1024 / 1024 / 1024).toFixed(1)}GB)
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={settings["model.local.model_id"] || ""}
                onChange={(e) => setSetting("model.local.model_id", e.target.value)}
                placeholder="qwen2.5:1.5b"
                className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                           focus:outline-none focus:border-primary-400"
              />
            )}
          </div>

          {/* 超时 */}
          <div>
            <label className="text-xs text-gray-500">{t("settings.model_timeout_sec")}</label>
            <input
              type="number"
              min={5}
              max={600}
              value={settings["model.timeout"] ?? 120}
              onChange={(e) => setSetting("model.timeout", Math.max(5, Math.min(600, Number(e.target.value) || 120)))}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            />
          </div>

          {/* 测试连接 */}
          <div>
            <button
              onClick={handleLocalTest}
              disabled={localTest.testing}
              className="w-full mt-1 text-xs px-3 py-1.5 rounded border transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed
                         bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {localTest.testing ? t("settings.model_testing") : t("settings.model_test_connection")}
            </button>
            {!localTest.testing && localTest.message && (
              <div
                className={`mt-1.5 text-xs px-2 py-1 rounded ${
                  localTest.success
                    ? "bg-green-50 text-green-700 border border-green-200"
                    : "bg-red-50 text-red-600 border border-red-200"
                }`}
              >
                {localTest.success ? "✅ " : "❌ "}{localTest.message}
              </div>
            )}
          </div>
        </>
      )}

      {/* 自动切换 */}
      <ToggleSetting
        label={t("settings.model_auto_switch")}
        description={t("settings.model_auto_switch_desc")}
        settingKey="model.auto_switch"
      />
    </div>
  );
}

// ============ 通用组件 ============

function ToggleSetting({
  label,
  description,
  settingKey,
}: {
  label: string;
  description?: string;
  settingKey: string;
}) {
  const value = useSettingsStore((s) => s.settings[settingKey]);
  const setSetting = useSettingsStore((s) => s.setSetting);

  return (
    <div className="flex items-center justify-between">
      <div>
        <span className="text-xs text-gray-700">{label}</span>
        {description && (
          <p className="text-xs text-gray-400">{description}</p>
        )}
      </div>
      <button
        onClick={() => setSetting(settingKey, !value)}
        className={`w-10 h-5 rounded-full transition-colors ${
          value ? "bg-primary-500" : "bg-gray-300"
        }`}
      >
        <div
          className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${
            value ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}
