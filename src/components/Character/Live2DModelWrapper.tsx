/**
 * Live2D 模型包装器
 * 负责模型加载、状态驱动 motion、鼠标跟踪
 */

import { useEffect, useRef, useState } from "react";
import type { Application } from "pixi.js";
import type { Live2DModelConfig } from "../../types/live2d";
import type { PersonaState } from "../../stores/agentStore";
import { loadModel, getMotionGroup } from "./live2dService";

interface Live2DModelWrapperProps {
  app: Application;
  config: Live2DModelConfig;
  state: PersonaState;
  size: number;
  ratio: number;
  onLoaded?: () => void;
  onError?: () => void;
}

export function Live2DModelWrapper({
  app,
  config,
  state,
  size,
  ratio,
  onLoaded,
  onError,
}: Live2DModelWrapperProps) {
  const modelRef = useRef<any>(null);
  const [error, setError] = useState<string | null>(null);

  // 加载模型
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError(null);
        console.log(`[Live2D] 开始加载模型: ${config.id} (${config.path})`);

        const model = await loadModel(config);
        if (cancelled) return;

        console.log(`[Live2D] 模型加载完成，添加到 stage`);

        // 清除旧模型
        if (modelRef.current) {
          try { app.stage.removeChild(modelRef.current); } catch {}
        }

        // 配置模型
        model.anchor.set(0.5, 0.5);
        model.x = size / 2;
        model.y = size / 2;

        // 保存模型原始尺寸（模型宽高会在 scale 后变化，仅记录一次）
        if (!(model as any).__origWidth) {
          (model as any).__origWidth = model.width || 800;
        }
        if (!(model as any).__origHeight) {
          (model as any).__origHeight = model.height || 800;
        }

        // 缩放模型适配窗口
        const target = size * ratio;
        const scaleX = target / ((model as any).__origWidth);
        const scaleY = target / ((model as any).__origHeight);
        const scale = Math.min(scaleX, scaleY) * 0.85; // 留 15% 边距
        model.scale.set(scale);

        // 启用交互（鼠标跟踪 + 点击）
        model.interactive = true;
        model.buttonMode = true;

        // 标记本次点击是否真正落在模型上（而非 canvas 空白区）
        model.on("pointerdown", () => {
          (window as any).__live2dModelClick = true;
        });

        app.stage.addChild(model);
        modelRef.current = model;
        onLoaded?.();
      } catch (e: any) {
        console.error(`[Live2D] 模型加载失败:`, e);
        if (!cancelled) {
          setError(e.message || "模型加载失败");
          onError?.();
        }
      }
    }

    load();

    return () => {
      cancelled = true;
      // 关键：组件卸载时移除当前模型
      if (modelRef.current) {
        try { app.stage.removeChild(modelRef.current); } catch {}
        modelRef.current = null;
      }
    };
  }, [config.id]); // 模型 ID 变化时重新加载

  // 状态变化 → 播放对应 motion
  useEffect(() => {
    if (!modelRef.current) return;

    const motionGroup = getMotionGroup(config, state);
    try {
      modelRef.current.motion(motionGroup);
    } catch {
      // 模型可能没有该 motion group，静默忽略
    }
  }, [state, config]);

  // 尺寸/比例变化时重新缩放
  useEffect(() => {
    if (!modelRef.current) return;
    const m = modelRef.current;
    const origW = (m as any).__origWidth || m.width || 800;
    const origH = (m as any).__origHeight || m.height || 800;
    const target = size * ratio;
    const scaleX = target / origW;
    const scaleY = target / origH;
    const scale = Math.min(scaleX, scaleY) * 0.85;
    m.scale.set(scale);
    m.x = size / 2;
    m.y = size / 2;
  }, [size, ratio, app]);

  if (error) {
    return null; // 加载失败时由外层 fallback 到 SVG
  }

  return null; // 模型直接渲染在 Pixi stage 上，无需 DOM 输出
}
