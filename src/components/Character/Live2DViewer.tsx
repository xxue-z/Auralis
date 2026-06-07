import { useState } from "react";
import { useSettingsStore } from "../../stores/settingsStore";

interface Props {
  onClick?: () => void;
}

export function Live2DViewer({ onClick }: Props) {
  const [isHovered, setIsHovered] = useState(false);
  const spriteSize = useSettingsStore((s) => s.settings["appearance.sprite_size"] || 96);
  const emojiSize = Math.round(spriteSize * 0.4);

  return (
    <div
      className="relative cursor-pointer select-none"
      style={{ width: spriteSize, height: spriteSize }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 圆形精灵 */}
      <div
        className="rounded-full bg-gradient-to-br from-primary-400 to-purple-400
                   flex items-center justify-center shadow-lg transition-transform
                   character-draggable w-full h-full"
        onClick={onClick}
      >
        <span style={{ fontSize: emojiSize }}>🧚</span>
      </div>
      {/* 提示文字 */}
      {isHovered && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap
                        text-xs text-gray-500 bg-white/80 px-2 py-0.5 rounded-full shadow">
          点击聊天
        </div>
      )}
    </div>
  );
}
