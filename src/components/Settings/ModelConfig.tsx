import { useState, useEffect } from "react";
import { useSettingsStore } from "../../stores/settingsStore";
import {
  fetchVendors,
  type Vendor,
} from "../../services/vendor-service";
import {
  checkOllamaStatus,
  listOllamaModels,
  type OllamaModel,
} from "../../services/ollama";

type Tab = "cloud" | "local";

export function ModelConfig() {
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
          ☁️ 云端模型
        </button>
        <button
          onClick={() => setTab("local")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            tab === "local"
              ? "bg-white text-gray-800 shadow-sm"
              : "text-gray-500"
          }`}
        >
          💻 本地模型
        </button>
      </div>

      {tab === "cloud" ? <CloudModelConfig /> : <LocalModelConfig />}
    </div>
  );
}

// ============ 云端模型配置 ============

function CloudModelConfig() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);

  const selectedVendor = settings["model.cloud.vendor"] || "OpenAI";
  const currentVendor = vendors.find((v) => v.vendor === selectedVendor);

  // 加载厂商列表
  useEffect(() => {
    fetchVendors().then((v) => {
      setVendors(v);
      setLoading(false);
    });
  }, []);

  // 选择厂商时自动填充
  const handleVendorChange = (vendorName: string) => {
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

  if (loading) {
    return <div className="text-xs text-gray-400 text-center py-4">加载中...</div>;
  }

  return (
    <div className="space-y-3">
      {/* 启用开关 */}
      <ToggleSetting
        label="启用云端模型"
        settingKey="model.cloud.enabled"
      />

      {settings["model.cloud.enabled"] && (
        <>
          {/* 厂商选择 */}
          <div>
            <label className="text-xs text-gray-500">厂商</label>
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
                  获取 Key →
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
            <label className="text-xs text-gray-500">API 地址</label>
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
            <label className="text-xs text-gray-500">API 协议</label>
            <select
              value={settings["model.cloud.api_protocol"] || "openai"}
              onChange={(e) => setSetting("model.cloud.api_protocol", e.target.value)}
              className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                         focus:outline-none focus:border-primary-400"
            >
              <option value="openai">OpenAI 兼容</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>

          {/* 模型选择 */}
          {currentVendor && currentVendor.models.length > 0 && (
            <div>
              <label className="text-xs text-gray-500">模型</label>
              <select
                value={settings["model.cloud.model_id"] || ""}
                onChange={(e) => setSetting("model.cloud.model_id", e.target.value)}
                className="w-full mt-1 text-xs px-2 py-1.5 border border-gray-200 rounded bg-white/80
                           focus:outline-none focus:border-primary-400"
              >
                {currentVendor.models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============ 本地模型配置（Ollama）============

function LocalModelConfig() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.setSetting);
  const [ollamaConnected, setOllamaConnected] = useState<boolean | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);

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

  return (
    <div className="space-y-3">
      {/* 启用开关 */}
      <ToggleSetting
        label="启用本地模型"
        settingKey="model.local.enabled"
      />

      {/* Ollama 引导 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-gray-600 space-y-1.5">
        <p className="font-medium text-gray-800">
          需要安装 Ollama 才能使用本地模型
        </p>
        <p>Ollama 是一个本地大模型运行框架，安装后 Auralis 可以离线使用 AI 能力。</p>
        <div className="flex gap-3">
          <a
            href="https://ollama.com/download"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-500 hover:underline"
          >
            📥 下载 Ollama
          </a>
          <a
            href="https://ollama.com/blog/openai-compatibility"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-500 hover:underline"
          >
            📖 配置文档
          </a>
        </div>
        <p className="text-gray-400">
          安装后运行: <code className="bg-gray-100 px-1 rounded">ollama pull qwen2.5:1.5b</code>
        </p>
      </div>

      {settings["model.local.enabled"] && (
        <>
          {/* 连接状态 */}
          <div className="flex items-center gap-2 text-xs">
            <span>状态:</span>
            {ollamaConnected === null ? (
              <span className="text-gray-400">检测中...</span>
            ) : ollamaConnected ? (
              <span className="text-green-600">🟢 已连接</span>
            ) : (
              <span className="text-red-500">🔴 未连接（请确认 Ollama 已启动）</span>
            )}
          </div>

          {/* API 地址 */}
          <div>
            <label className="text-xs text-gray-500">Ollama 地址</label>
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
            <label className="text-xs text-gray-500">模型</label>
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
        </>
      )}

      {/* 自动切换 */}
      <ToggleSetting
        label="自动切换"
        description="云端不可用时自动切换到本地模型"
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
