/**
 * 角色查看器
 * 支持 Live2D 模型 和 SVG fallback
 *
 * 策略：先在后台加载模型数据，加载完成后再渲染 PixiCanvas
 * 这样避免了空画布遮挡 SVG 的问题
 */

import { useState, useEffect, useCallback } from "react";
import { useSettingsStore } from "../../stores/settingsStore";
import { useAgentStore } from "../../stores/agentStore";
import { CharacterSVG } from "./CharacterSVG";
import { PixiCanvas } from "./PixiCanvas";
import { Live2DModelWrapper } from "./Live2DModelWrapper";
import { loadRegistry, getModel, loadModel } from "./live2dService";
import type { Live2DModelConfig } from "../../types/live2d";
import "./CharacterAnimations.css";

interface Props {
  onClick?: () => void;
}

export function Live2DViewer({ onClick }: Props) {
  const [isHovered, setIsHovered] = useState(false);
  const [pixiApp, setPixiApp] = useState<any>(null);
  const [modelConfig, setModelConfig] = useState<Live2DModelConfig | null>(null);
  const [modelReady, setModelReady] = useState(false);
  const [modelFailed, setModelFailed] = useState(false);
  const [registryLoaded, setRegistryLoaded] = useState(false);

  const spriteSize = useSettingsStore((s) => s.settings["appearance.sprite_size"] || 96);
  const modelId = useSettingsStore((s) => s.settings["appearance.model_id"] || "svg_fallback");
  const personaState = useAgentStore((s) => s.personaState);

  useEffect(() => {
    loadRegistry().then(() => setRegistryLoaded(true));
  }, []);

  // 当 modelId 变化时，后台预加载模型
  useEffect(() => {
    if (!registryLoaded) return;
    if (modelId === "svg_fallback") {
      setModelConfig(null);
      setModelReady(false);
      setModelFailed(false);
      setPixiApp(null);
      return;
    }

    const config = getModel(modelId);
    if (!config) {
      setModelConfig(null);
      return;
    }

    setModelConfig(config);
    setModelReady(false);
    setModelFailed(false);
    setPixiApp(null);

    // 后台加载模型数据（不需要 PixiCanvas）
    let cancelled = false;
    loadModel(config)
      .then(() => {
        if (!cancelled) {
          console.log(`[Live2D] 模型预加载完成: ${config.id}`);
          setModelReady(true);
        }
      })
      .catch((e) => {
        console.error(`[Live2D] 模型预加载失败:`, e);
        if (!cancelled) {
          setModelFailed(true);
        }
      });

    return () => { cancelled = true; };
  }, [modelId, registryLoaded]);

  const handlePixiApp = useCallback((app: any) => setPixiApp(app), []);

  // 只有模型预加载完成后才渲染 PixiCanvas
  const showLive2D = modelReady && !modelFailed && modelConfig !== null;
  // Live2D 模型使用较大显示区域，SVG 使用 spriteSize
  const live2dSize = showLive2D ? 200 : 0;
  const displaySize = showLive2D ? live2dSize : spriteSize;

  // Live2D 模式下自动调整窗口大小
  useEffect(() => {
    if (showLive2D) {
      import("@tauri-apps/api/core").then(({ invoke }) => {
        // 窗口尺寸 = 模型显示区域 + 底部留白
        const winSize = displaySize + 40;
        invoke("resize_window", { width: winSize, height: winSize, spriteSize: displaySize }).catch(() => {});
      });
    }
  }, [showLive2D, displaySize]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onClick?.();
  }, [onClick]);

  return (
    <div
      className="relative cursor-pointer select-none character-container character-draggable"
      style={{ width: displaySize, height: displaySize }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
    >
      {showLive2D && modelConfig ? (
        /* Live2D 模式 — 模型已预加载，直接渲染 */
        <>
          <PixiCanvas
            key={`canvas-${modelConfig.id}`}
            width={displaySize}
            height={displaySize}
            onApp={handlePixiApp}
          />
          {pixiApp && (
            <Live2DModelWrapper
              key={modelConfig.id}
              app={pixiApp}
              config={modelConfig}
              state={personaState}
              size={displaySize}
            />
          )}
        </>
      ) : (
        /* SVG 模式（默认 / 加载中 / 加载失败） */
        <CharacterSVG state={personaState} size={spriteSize} />
      )}

      {isHovered && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 whitespace-nowrap
                        text-xs text-gray-500 bg-white/80 px-2 py-0.5 rounded-full shadow
                        animate-pulse z-20">
          点击聊天
        </div>
      )}

      {personaState === "thinking" && (
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 z-20">
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        </div>
      )}
    </div>
  );
}
