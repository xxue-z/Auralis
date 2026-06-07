import { useState } from "react";

interface Props {
  onClick?: () => void;
  onRightClick?: () => void;
}

export function Live2DViewer({ onClick, onRightClick }: Props) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="character-draggable cursor-pointer select-none"
      onClick={onClick}
      onContextMenu={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onRightClick?.();
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={`w-24 h-24 rounded-full bg-gradient-to-br from-primary-400 to-purple-400
                    flex items-center justify-center shadow-lg transition-transform
                    ${isHovered ? "scale-110" : "scale-100"}`}
      >
        <span className="text-4xl">🧚</span>
      </div>
      {isHovered && (
        <div className="text-center text-xs text-gray-500 mt-1">
          左键聊天 · 右键设置
        </div>
      )}
    </div>
  );
}
