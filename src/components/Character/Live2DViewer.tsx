/**
 * 角色查看器
 * 支持 Live2D 模型 和 SVG fallback
 *
 * 策略：先在后台加载模型数据，加载完成后再渲染 PixiCanvas
 * 这样避免了空画布遮挡 SVG 的问题
 */

import { useState, useEffect, useCallback } from "react";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import { PhysicalSize } from "@tauri-apps/api/dpi";
import { listen } from "@tauri-apps/api/event";
import { useSettingsStore } from "../../stores/settingsStore";
import { useAgentStore } from "../../stores/agentStore";
import { CharacterSVG } from "./CharacterSVG";
import { PixiCanvas } from "./PixiCanvas";
import { Live2DModelWrapper } from "./Live2DModelWrapper";
import { loadRegistry, getModel, addModel, loadModel } from "./live2dService";
import type { Live2DModelConfig } from "../../types/live2d";
import "./CharacterAnimations.css";

interface Props {
  // 点击由父组件的 pointerUp 统一处理，不再通过 onClick prop
}

export function Live2DViewer(_props: Props) {
  const [pixiApp, setPixiApp] = useState<any>(null);
  const [modelConfig, setModelConfig] = useState<Live2DModelConfig | null>(null);
  const [modelReady, setModelReady] = useState(false);
  const [modelFailed, setModelFailed] = useState(false);
  const [registryLoaded, setRegistryLoaded] = useState(false);

  const settings = useSettingsStore((s) => s.settings);
  const modelId = settings["appearance.model_id"] || "svg_fallback";
  const spriteSize = settings[`model:${modelId}:sprite_size`] ?? settings["appearance.sprite_size"] ?? 96;
  const spriteOpacity = settings[`model:${modelId}:sprite_opacity`] ?? settings["appearance.sprite_opacity"] ?? 1;
  const ratio = settings[`model:${modelId}:window_ratio`] ?? 1.0;
  const personaState = useAgentStore((s) => s.personaState);

  useEffect(() => {
    loadRegistry().then(() => {
      // 从 localStorage 恢复已导入的模型（跨窗口同步）
      try {
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key?.startsWith("imported_model:")) {
            const raw = localStorage.getItem(key);
            if (raw) {
              const config = JSON.parse(raw) as Live2DModelConfig;
              addModel(config);
            }
          }
        }
      } catch {}
      setRegistryLoaded(true);
    });
  }, []);

  // 监听其他窗口导入的模型事件
  useEffect(() => {
    const unlisten = listen<Live2DModelConfig>("model-imported", (e) => {
      addModel(e.payload);
    });
    return () => { unlisten.then((fn) => fn()); };
  }, []);

  // 当 modelId 变化时，后台预加载模型
  useEffect(() => {
    if (!registryLoaded) return;
    if (modelId === "svg_fallback") {
      setModelConfig(null);
      setModelReady(false);
      setModelFailed(false);
      return;
    }

    let config = getModel(modelId);
    if (!config) {
      // 尝试从 localStorage 恢复（跨窗口同步未完成时的回退）
      try {
        const raw = localStorage.getItem(`imported_model:${modelId}`);
        if (raw) {
          config = JSON.parse(raw) as Live2DModelConfig;
          addModel(config);
        }
      } catch {}
    }
    if (!config) {
      setModelConfig(null);
      return;
    }

    setModelConfig(config);
    setModelReady(false);
    setModelFailed(false);

    // 在模型开始加载前确保 Pixi canvas 尺寸正确
    if (pixiApp) {
      pixiApp.renderer.resize(displaySize, displaySize);
    }

    // 后台加载模型数据
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

  const displaySize = spriteSize;

  // 精灵大小变化时调整窗口大小，同步确保 Pixi canvas 尺寸
  useEffect(() => {
    const winSize = displaySize + 40;
    const appWindow = getCurrentWebviewWindow();
    appWindow.setSize(new PhysicalSize(winSize, winSize)).catch(() => {});
    if (pixiApp) {
      pixiApp.renderer.resize(displaySize, displaySize);
    }
  }, [displaySize, pixiApp]);

  return (
    <div
      className="relative cursor-pointer select-none character-container character-draggable"
      style={{ width: displaySize, height: displaySize, opacity: spriteOpacity }}
    >
      {/* PixiCanvas 常驻：选中 Live2D 模型后即使加载中也保持 */}
      {modelId !== "svg_fallback" && !modelFailed && (
        <PixiCanvas
          width={displaySize}
          height={displaySize}
          onApp={handlePixiApp}
        />
      )}

      {/* Live2D 模型（只读加载完成后才渲染） */}
      {pixiApp && modelConfig && modelReady && (
        <Live2DModelWrapper
          key={modelConfig.id}
          app={pixiApp}
          config={modelConfig}
          state={personaState}
          size={displaySize}
          ratio={ratio}
        />
      )}

      {/* SVG 回退 */}
      {(modelId === "svg_fallback" || modelFailed) && (
        <CharacterSVG state={personaState} size={spriteSize} />
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
