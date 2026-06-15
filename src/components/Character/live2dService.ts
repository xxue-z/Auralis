/**
 * Live2D 模型加载/缓存服务
 */

import { convertFileSrc } from "@tauri-apps/api/core";
import type { Live2DModelConfig, ModelRegistry } from "../../types/live2d";

// Cubism 4 框架是否已注册
let _frameworkRegistered = false;
let _coreLoadPromise: Promise<void> | null = null;

/**
 * 加载 Cubism Core SDK 运行时（live2dcubismcore.min.js）
 * pixi-live2d-display 必需此文件才能加载 .moc3 模型
 *
 * 关键：必须在 import("pixi-live2d-display/cubism4") 之前加载完成，
 * 因为 cubism4 模块在加载时就检查 window.Live2DCubismCore
 */
function loadCubismCore(): Promise<void> {
  if (_coreLoadPromise) return _coreLoadPromise;

  _coreLoadPromise = new Promise((resolve, reject) => {
    // 已加载则跳过
    if ((window as any).Live2DCubismCore) {
      console.log("[Live2D] Cubism Core SDK 已存在");
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = "/live2dcubismcore.min.js";
    // 不使用 async！必须同步加载完成才能 import cubism4
    script.onload = () => {
      console.log("[Live2D] Cubism Core SDK 加载成功");
      resolve();
    };
    script.onerror = () => {
      console.error("[Live2D] Cubism Core SDK 加载失败: /live2dcubismcore.min.js");
      _coreLoadPromise = null; // 允许重试
      reject(new Error("Cubism Core SDK 加载失败"));
    };
    document.head.appendChild(script);
  });

  return _coreLoadPromise;
}

/**
 * 注册 Cubism 4 框架（只需调用一次）
 */
async function ensureFramework() {
  if (_frameworkRegistered) return;

  // 关键：先加载 Cubism Core，等待完成后再 import cubism4
  await loadCubismCore();

  // 确认 Live2DCubismCore 已就位
  if (!(window as any).Live2DCubismCore) {
    throw new Error("Cubism Core 加载后仍未找到 window.Live2DCubismCore");
  }

  const { Live2DModel } = await import("pixi-live2d-display/cubism4");
  // registerTicker 需要一个有 .shared 属性的对象
  // PixiJS v6 Ticker.shared 就是全局 ticker 实例
  const PIXI = await import("pixi.js");
  const ticker = PIXI.Ticker.shared || new PIXI.Ticker();
  // 包装成 cubism4 期望的格式 { shared: tickerInstance }
  (Live2DModel as any).registerTicker({ shared: ticker });
  _frameworkRegistered = true;
  console.log("[Live2D] Cubism 4 框架已注册");
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
 * 加载 Live2D 模型（带缓存）
 */
export async function loadModel(config: Live2DModelConfig): Promise<any> {
  if (_modelCache.has(config.id)) {
    return _modelCache.get(config.id);
  }

  // 确保 Cubism 4 框架已注册
  await ensureFramework();

  const { Live2DModel } = await import("pixi-live2d-display/cubism4");

  // 解析原始文件路径：逐层剥离可能累积的 asset 协议前缀
  // （兼容跨窗口同步或旧版本存储时 path 已被 convertFileSrc 转换的情况）
  function resolveRawPath(p: string): string {
    const assetRe = /^https?:\/\/asset\.localhost\//;
    let cur = p;
    while (assetRe.test(cur)) {
      cur = decodeURIComponent(cur.replace(assetRe, ''));
    }
    return cur;
  }

  const modelPath = config.type === "imported"
    ? convertFileSrc(resolveRawPath(config.path))
    : config.path;
  console.log(`[Live2D] 加载模型: ${modelPath}`, { id: config.id, type: config.type, rawPath: config.path });
  try {
    const model = await Live2DModel.from(modelPath);
    console.log(`[Live2D] 模型加载成功: ${config.id}`);
    _modelCache.set(config.id, model);
    return model;
  } catch (e) {
    console.error(`[Live2D] 模型加载失败: ${config.id}`, {
      error: e,
      modelPath,
      type: config.type,
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
