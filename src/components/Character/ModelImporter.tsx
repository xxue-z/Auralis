/**
 * Live2D 模型导入器
 * 支持 .zip 文件解压并注册为可用模型
 */

import { useState, useRef } from "react";
import JSZip from "jszip";
import { addModel } from "./live2dService";
import type { Live2DModelConfig } from "../../types/live2d";

interface ModelImporterProps {
  onImported?: (config: Live2DModelConfig) => void;
}

export function ModelImporter({ onImported }: ModelImporterProps) {
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setError(null);

    try {
      const buffer = await file.arrayBuffer();
      const zip = await JSZip.loadAsync(buffer);

      // 查找 model3.json（Cubism 4）或 model.json（Cubism 2）
      let modelJsonPath: string | null = null;

      zip.forEach((path) => {
        if (path.endsWith(".model3.json") || path.endsWith(".model.json")) {
          modelJsonPath = path;
        }
      });

      if (!modelJsonPath) {
        throw new Error("ZIP 中未找到 Live2D 模型文件（.model3.json 或 .model.json）");
      }

      // 解压所有文件到内存
      const files: Record<string, Uint8Array> = {};
      for (const [path, entry] of Object.entries(zip.files)) {
        if (!entry.dir) {
          const data = await entry.async("uint8array");
          files[path] = data;
        }
      }

      // 生成模型 ID（基于文件名）
      const jsonPath: string = modelJsonPath;
      const segments = jsonPath.split("/");
      const dirName = segments.length > 1 ? segments[0] : file.name.replace(".zip", "");
      const modelId = `imported_${dirName}`;

      // 将文件转为 Blob URL（浏览器端临时存储）
      const blobUrls: Record<string, string> = {};
      for (const [path, data] of Object.entries(files)) {
        const buf = data.buffer instanceof ArrayBuffer ? data.buffer : new Uint8Array(data).buffer;
        blobUrls[path] = URL.createObjectURL(new Blob([buf]));
      }

      // 构建模型配置
      const config: Live2DModelConfig = {
        id: modelId,
        name: dirName,
        nameEn: dirName,
        path: blobUrls[jsonPath] || "",
        type: "imported",
        mappings: {
          idle: "idle",
          speaking: "tap",
          thinking: "tap",
          happy: "tap",
        },
      };

      addModel(config);
      onImported?.(config);
    } catch (e: any) {
      setError(e.message || "导入失败");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div>
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
        className="w-full py-2 text-xs text-gray-600 bg-gray-50 border border-gray-200
                   rounded-lg hover:bg-gray-100 disabled:opacity-50 transition-colors"
      >
        {importing ? "导入中..." : "📦 导入 Live2D 模型（.zip）"}
      </button>
      {error && (
        <p className="text-xs text-red-500 mt-1">{error}</p>
      )}
    </div>
  );
}
