import { useState, useRef, useEffect } from "react";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { addModel } from "./live2dService";
import type { Live2DModelConfig } from "../../types/live2d";

interface ExtractModelResult {
  model_id: string;
  model_name: string;
  model_dir: string;
  model_json_path: string;
}

interface ExtractProgress {
  current: number;
  total: number;
  file: string;
}

interface ModelImporterProps {
  onImported?: (config: Live2DModelConfig) => void;
}

export function ModelImporter({ onImported }: ModelImporterProps) {
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastModel, setLastModel] = useState<ExtractModelResult | null>(null);
  const [progress, setProgress] = useState<ExtractProgress | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const unlistenRef = useRef<UnlistenFn | null>(null);

  useEffect(() => {
    return () => {
      unlistenRef.current?.();
    };
  }, []);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setError(null);
    setLastModel(null);
    setProgress(null);

    // 让 UI 先渲染"导入中..."状态
    await new Promise((r) => setTimeout(r, 50));

    // 监听 Rust 进度事件
    const unlisten = await listen<ExtractProgress>("import-progress", (e) => {
      setProgress(e.payload);
    });
    unlistenRef.current = unlisten;

    try {
      const buffer = await file.arrayBuffer();
      const zipData = new Uint8Array(buffer);

      // 直接传入 Uint8Array，Tauri IPC 以二进制传输（避免 JSON 序列化大数组）
      const result = await invoke<ExtractModelResult>("extract_model_zip", {
        zipData,
      });

      const assetUrl = convertFileSrc(
        `${result.model_dir}/${result.model_json_path}`
      );

      const config: Live2DModelConfig = {
        id: result.model_id,
        name: result.model_name,
        nameEn: result.model_name,
        path: assetUrl,
        type: "imported",
        modelDir: result.model_dir,
        mappings: {
          idle: "idle",
          speaking: "tap",
          thinking: "tap",
          happy: "tap",
        },
      };

      addModel(config);
      setLastModel(result);
      onImported?.(config);
    } catch (e: any) {
      setError(e.message || e || "导入失败");
    } finally {
      unlistenRef.current?.();
      unlistenRef.current = null;
      setImporting(false);
      setProgress(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const pct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : null;

  return (
    <div className="space-y-2">
      <input
        ref={fileRef}
        type="file"
        accept=".zip"
        onChange={handleImport}
        className="hidden"
      />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={importing}
        className="relative w-full py-2 text-xs text-gray-600 bg-gray-50 border border-gray-200
                   rounded-lg hover:bg-gray-100 disabled:opacity-50 transition-colors overflow-hidden"
      >
        {importing && pct !== null && (
          <span
            className="absolute inset-0 bg-primary-100 transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        )}
        <span className="relative z-10">
          {importing
            ? `导入中... ${pct !== null ? `${pct}%` : ""}`
            : "📦 导入 Live2D 模型（.zip）"}
        </span>
      </button>
      {error && (
        <p className="text-xs text-red-500 mt-1">{error}</p>
      )}
      {lastModel && (
        <div className="text-xs text-gray-500 space-y-1 mt-2 p-2 bg-gray-50 rounded-lg">
          <p className="truncate" title={lastModel.model_dir}>
            存储位置：{lastModel.model_dir}
          </p>
          <button
            onClick={() => invoke("open_in_explorer", { path: lastModel.model_dir })}
            className="text-blue-500 hover:text-blue-700 underline"
          >
            打开文件夹
          </button>
        </div>
      )}
    </div>
  );
}
