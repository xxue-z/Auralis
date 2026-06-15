/**
 * 模型选择器
 * 显示可用模型列表，支持切换
 */

import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useSettingsStore } from "../../stores/settingsStore";
import { loadRegistry, getModels } from "./live2dService";
import { ModelImporter } from "./ModelImporter";
import type { Live2DModelConfig } from "../../types/live2d";

export function ModelSelector() {
  const [models, setModels] = useState<Live2DModelConfig[]>([]);
  const [saved, setSaved] = useState(false);
  const settings = useSettingsStore((s) => s.settings);
  const currentModelId = settings["appearance.model_id"] || "svg_fallback";
  const setSetting = useSettingsStore((s) => s.setSetting);

  useEffect(() => {
    loadRegistry().then(() => {
      setModels(getModels());
    });
  }, []);

  const handleSelect = (modelId: string) => {
    setSetting("appearance.model_id", modelId);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="space-y-3">
      <label className="text-xs text-gray-500 block">角色模型</label>

      {/* SVG Fallback 选项 */}
      <button
        onClick={() => handleSelect("svg_fallback")}
        className={`w-full p-2 rounded-lg text-xs text-left transition-all ${
          currentModelId === "svg_fallback"
            ? "bg-primary-50 border border-primary-300 text-primary-700"
            : "bg-gray-50 border border-gray-100 text-gray-600 hover:bg-gray-100"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="font-medium">🎨 默认精灵</div>
          {currentModelId === "svg_fallback" && <span className="text-primary-500">✓</span>}
        </div>
        <div className="text-[10px] opacity-60">SVG 矢量角色（无需模型）</div>
      </button>

      {/* Live2D 模型列表 */}
      {models.map((model) => (
        <div
          key={model.id}
          className={`w-full p-2 rounded-lg text-xs text-left transition-all ${
            currentModelId === model.id
              ? "bg-primary-50 border border-primary-300 text-primary-700"
              : "bg-gray-50 border border-gray-100 text-gray-600 hover:bg-gray-100"
          }`}
        >
          <button
            onClick={() => handleSelect(model.id)}
            className="w-full text-left"
          >
            <div className="flex items-center justify-between">
              <div className="font-medium">
                {model.type === "imported" ? "📥 " : "🎭 "}
                {model.name}
              </div>
              {currentModelId === model.id && <span className="text-primary-500">✓</span>}
            </div>
            <div className="text-[10px] opacity-60">
              {model.nameEn} · {model.type === "bundled" ? "内置" : "已导入"}
            </div>
          </button>
          {model.type === "imported" && model.modelDir && (
            <div className="mt-1 pt-1 border-t border-gray-200 flex items-center justify-between">
              <span className="text-[10px] text-gray-400 truncate max-w-[200px]" title={model.modelDir}>
                {model.modelDir}
              </span>
              <button
                onClick={() => invoke("open_in_explorer", { path: model.modelDir })}
                className="text-blue-500 hover:text-blue-700 text-[10px] shrink-0 ml-1"
              >
                打开
              </button>
            </div>
          )}
        </div>
      ))}

      {models.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-2">加载模型列表中...</p>
      )}

      {/* 导入按钮 */}
      <ModelImporter onImported={() => {
        setModels([...getModels()]);
      }} />

      {/* 保存提示 */}
      {saved && (
        <div className="text-xs text-center text-green-600 py-1 animate-pulse">
          ✅ 已应用
        </div>
      )}
    </div>
  );
}
