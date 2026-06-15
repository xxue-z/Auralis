/**
 * Live2D 模型加载/缓存服务
 */

import { convertFileSrc } from "@tauri-apps/api/core";
import type { Live2DModelConfig, ModelRegistry } from "../../types/live2d";

// Cubism 框架注册状态（按版本）
let _frameworkState = { 2: false, 4: false };
let _coreLoadPromise: { [key: number]: Promise<void> | null } = { 2: null, 4: null };

/**
 * 加载 Cubism Core SDK 运行时
 * v4: live2dcubismcore.min.js → window.Live2DCubismCore
 * v2: live2d.min.js → window.Live2D
 *
 * 必须在 import cubism4/cubism2 之前加载完成，
 * 因为模块在加载时就检查对应的全局变量
 */
function loadCubismCore(version: 2 | 4): Promise<void> {
  if (_coreLoadPromise[version]) return _coreLoadPromise[version]!;

  const isV4 = version === 4;
  const globalKey = isV4 ? "Live2DCubismCore" : "Live2D";
  const src = isV4 ? "/live2dcubismcore.min.js" : "/live2d.min.js";

  _coreLoadPromise[version] = new Promise((resolve, reject) => {
    if ((window as any)[globalKey]) {
      console.log(`[Live2D] Cubism ${version} Core SDK 已存在`);
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.onload = () => {
      console.log(`[Live2D] Cubism ${version} Core SDK 加载成功`);
      resolve();
    };
    script.onerror = () => {
      console.error(`[Live2D] Cubism ${version} Core SDK 加载失败: ${src}`);
      _coreLoadPromise[version] = null;
      reject(new Error(`Cubism ${version} Core SDK 加载失败`));
    };
    document.head.appendChild(script);
  });

  return _coreLoadPromise[version]!;
}

/**
 * 注册指定版本的 Cubism 框架
 * 返回该版本的 Live2DModel 类
 */
async function ensureFramework(version: 2 | 4): Promise<any> {
  if (!_frameworkState[version]) {
    await loadCubismCore(version);
    const globalKey = version === 4 ? "Live2DCubismCore" : "Live2D";
    if (!(window as any)[globalKey]) {
      throw new Error(`Cubism ${version} Core 加载后仍未找到 window.${globalKey}`);
    }

    const PIXI = await import("pixi.js");
    const ticker = PIXI.Ticker.shared || new PIXI.Ticker();

    if (version === 4) {
      const { Live2DModel } = await import("pixi-live2d-display/cubism4");
      (Live2DModel as any).registerTicker({ shared: ticker });
    } else {
      const { Live2DModel } = await import("pixi-live2d-display/cubism2");
      (Live2DModel as any).registerTicker({ shared: ticker });
    }
    _frameworkState[version] = true;
    console.log(`[Live2D] Cubism ${version} 框架已注册`);
  }

  if (version === 4) {
    const { Live2DModel } = await import("pixi-live2d-display/cubism4");
    return Live2DModel;
  } else {
    const { Live2DModel } = await import("pixi-live2d-display/cubism2");
    return Live2DModel;
  }
}

// 内置模型注册表（从 public/models/registry.json 加载）
let _registry: ModelRegistry = { models: [] };

// 模型实例缓存
const _modelCache = new Map<string, any>();

/**
 * 加载模型注册表
 */
export async function loadRegistry(): Promise<ModelRegistry> {
  try {
    const resp = await fetch("/models/registry.json");
    _registry = await resp.json();
  } catch {
    console.warn("[Live2D] 无法加载 registry.json，使用空注册表");
    _registry = { models: [] };
  }
  return _registry;
}

/**
 * 获取所有可用模型
 */
export function getModels(): Live2DModelConfig[] {
  return _registry.models;
}

/**
 * 根据 ID 获取模型配置
 */
export function getModel(id: string): Live2DModelConfig | undefined {
  return _registry.models.find((m) => m.id === id);
}

/**
 * 添加导入的模型到注册表
 */
export function addModel(config: Live2DModelConfig): void {
  const existing = _registry.models.findIndex((m) => m.id === config.id);
  if (existing >= 0) {
    _registry.models[existing] = config;
  } else {
    _registry.models.push(config);
  }
}

/**
 * 从注册表移除已导入的模型
 */
export function removeModel(id: string): void {
  const idx = _registry.models.findIndex((m) => m.id === id && m.type === "imported");
  if (idx >= 0) {
    _registry.models.splice(idx, 1);
  }
  releaseModel(id);
  try {
    localStorage.removeItem(`imported_model:${id}`);
  } catch {}
}

/**
 * 获取模型对应的 Cubism 版本
 */
function getCubismVersion(config: Live2DModelConfig): 2 | 4 {
  if (config.cubismVersion === 2) return 2;
  return 4;
}

/**
 * 解析原始文件路径：逐层剥离可能累积的 asset 协议前缀
 */
function resolveRawPath(p: string): string {
  const assetRe = /^https?:\/\/asset\.localhost\//;
  let cur = p;
  while (assetRe.test(cur)) {
    cur = decodeURIComponent(cur.replace(assetRe, ''));
  }
  return cur;
}

/**
 * 将 model.json 中所有相对路径改写为绝对 asset 协议 URL
 * 解决 Windows 路径编码导致 pixi-live2d-display 路径解析错误的问题
 */
async function fetchModelWithAbsoluteUrls(rawJsonPath: string): Promise<any> {
  const jsonUrl = convertFileSrc(rawJsonPath);
  const resp = await fetch(jsonUrl);
  const data = await resp.json();

  // 提取目录部分，统一为反斜杠（Windows convertFileSrc 需要）
  const sepIdx = Math.max(rawJsonPath.lastIndexOf('/'), rawJsonPath.lastIndexOf('\\'));
  const rawDir = sepIdx >= 0 ? rawJsonPath.substring(0, sepIdx) : '';

  function toAbs(relative: string): string {
    if (!relative) return relative;
    // convertFileSrc 在 Windows 上需要反斜杠路径
    const absPath = `${rawDir}\\${relative}`.replace(/\//g, '\\');
    return convertFileSrc(absPath);
  }

  // pixi-live2d-display 的 ModelSettings 需要 url 字段
  data.url = jsonUrl;

  // Cubism 2 格式
  if (data.model || !data.FileReferences) {
    if (data.model) data.model = toAbs(data.model);
    if (data.textures) data.textures = data.textures.map(toAbs);
    if (data.physics) data.physics = toAbs(data.physics);
    if (data.pose) data.pose = toAbs(data.pose);
    if (data.motions) {
      for (const group of Object.keys(data.motions)) {
        data.motions[group] = data.motions[group].map((m: any) => ({ ...m, file: toAbs(m.file) }));
      }
    }
    if (data.expressions) {
      data.expressions = data.expressions.map((e: any) => ({ ...e, file: toAbs(e.file) }));
    }
    return data;
  }

  // Cubism 3/4 格式
  const fr = data.FileReferences;
  if (fr) {
    if (fr.Moc) fr.Moc = toAbs(fr.Moc);
    if (fr.Textures) fr.Textures = fr.Textures.map(toAbs);
    if (fr.Physics) fr.Physics = toAbs(fr.Physics);
    if (fr.Pose) fr.Pose = toAbs(fr.Pose);
    if (fr.Motions) {
      for (const group of Object.keys(fr.Motions)) {
        fr.Motions[group] = fr.Motions[group].map((m: any) => ({ ...m, File: toAbs(m.File) }));
      }
    }
    if (fr.Expressions) {
      fr.Expressions = fr.Expressions.map((e: any) => ({ ...e, File: toAbs(e.File) }));
    }
  }
  return data;
}

/**
 * 加载 Live2D 模型（带缓存）
 */
export async function loadModel(config: Live2DModelConfig): Promise<any> {
  if (_modelCache.has(config.id)) {
    return _modelCache.get(config.id);
  }

  const version = getCubismVersion(config);
  const Live2DModel = await ensureFramework(version);

  const rawPath = resolveRawPath(config.path);

  try {
    let model: any;

    if (config.type === "imported") {
      // import 模型：手动加载 JSON 并改写为绝对路径
      const modelData = await fetchModelWithAbsoluteUrls(rawPath);
      model = await Live2DModel.from(modelData);
    } else {
      // bundled 模型：直接使用内置 URL
      model = await Live2DModel.from(config.path);
    }

    console.log(`[Live2D] 模型加载成功: ${config.id}`);
    _modelCache.set(config.id, model);
    return model;
  } catch (e) {
    console.error(`[Live2D] 模型加载失败: ${config.id}`, {
      error: e,
      type: config.type,
      version,
      rawPath: config.path,
    });
    throw e;
  }
}

/**
 * 释放模型缓存
 */
export function releaseModel(id: string): void {
  const model = _modelCache.get(id);
  if (model) {
    model.destroy?.();
    _modelCache.delete(id);
  }
}

/**
 * 获取状态对应的 motion group 名称
 */
export function getMotionGroup(
  config: Live2DModelConfig,
  state: string,
): string {
  return config.mappings[state as keyof typeof config.mappings] || "idle";
}
