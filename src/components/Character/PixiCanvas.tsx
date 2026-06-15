/**
 * Pixi.js 透明 WebGL 画布
 * 管理 Application 生命周期，暴露 stage 给子组件
 */

import { useEffect, useRef } from "react";

interface PixiCanvasProps {
  width: number;
  height: number;
  className?: string;
  onApp?: (app: any) => void;
}

export function PixiCanvas({ width, height, className, onApp }: PixiCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const appRef = useRef<any>(null);
  const sizeRef = useRef({ width, height });
  sizeRef.current = { width, height };

  useEffect(() => {
    if (!canvasRef.current || appRef.current) return;

    let cancelled = false;

    import("pixi.js").then((PIXI) => {
      if (cancelled || !canvasRef.current) return;
      // Use ref to avoid stale closure on width/height
      const { width: w, height: h } = sizeRef.current;

      const app = new PIXI.Application({
        view: canvasRef.current,
        width: w,
        height: h,
        backgroundAlpha: 0,      // 透明背景（v6.5+）
        backgroundColor: 0x000000,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
        antialias: true,
      });

      appRef.current = app;
      onApp?.(app);
    });

    return () => {
      cancelled = true;
      if (appRef.current) {
        try { appRef.current.destroy(true); } catch {}
        appRef.current = null;
      }
    };
  }, []); // 只在挂载时创建

  // 尺寸变化时更新
  useEffect(() => {
    if (appRef.current) {
      appRef.current.renderer.resize(width, height);
    }
  }, [width, height]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ width, height, background: "transparent" }}
    />
  );
}
