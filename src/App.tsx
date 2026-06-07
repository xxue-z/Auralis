import { useState, useEffect } from "react";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { ConfirmDialog } from "./components/Chat/ConfirmDialog";
import { Live2DViewer } from "./components/Character/Live2DViewer";
import { SettingsPanel } from "./components/Settings/SettingsPanel";

function App() {
  const [showChat, setShowChat] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // 监听托盘菜单的 "open-settings" 事件
  useEffect(() => {
    const handler = () => setShowSettings(true);
    window.addEventListener("open-settings", handler);
    return () => window.removeEventListener("open-settings", handler);
  }, []);

  // 右键精灵 → 打开设置
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setShowSettings(true);
  };

  return (
    <div
      className="min-h-screen bg-transparent flex flex-col items-end justify-end p-4 gap-2"
      onContextMenu={handleContextMenu}
    >
      {showChat && (
        <div className="w-80 h-96">
          <ChatPanel />
        </div>
      )}

      <Live2DViewer
        onClick={() => setShowChat(!showChat)}
        onRightClick={() => setShowSettings(true)}
      />

      {/* 设置面板 */}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}

      {/* 操作确认弹窗（全局） */}
      <ConfirmDialog />
    </div>
  );
}

export default App;
