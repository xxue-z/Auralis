import { useState } from "react";
import { useSettingsStore } from "../../stores/settingsStore";
import { useAgentStore } from "../../stores/agentStore";
import { CharacterSVG } from "./CharacterSVG";
import "./CharacterAnimations.css";

interface Props {
  onClick?: () => void;
}

export function Live2DViewer({ onClick }: Props) {
  const [isHovered, setIsHovered] = useState(false);
  const spriteSize = useSettingsStore((s) => s.settings["appearance.sprite_size"] || 96);
  const personaState = useAgentStore((s) => s.personaState);

  return (
    <div
      className="relative cursor-pointer select-none character-container"
      style={{ width: spriteSize, height: spriteSize }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* SVG 角色 */}
      <CharacterSVG state={personaState} size={spriteSize} />

      {/* 提示文字 */}
      {isHovered && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap
                        text-xs text-gray-500 bg-white/80 px-2 py-0.5 rounded-full shadow
                        animate-pulse">
          点击聊天
        </div>
      )}

      {/* 状态指示器 — 思考时显示加载点 */}
      {personaState === "thinking" && (
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
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
