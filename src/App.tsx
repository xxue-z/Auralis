import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { ConfirmDialog } from "./components/Chat/ConfirmDialog";
import { Live2DViewer } from "./components/Character/Live2DViewer";
import { SettingsPanel } from "./components/Settings/SettingsPanel";
import { OnboardingWizard } from "./components/Onboarding/Wizard";
import { useSettingsStore } from "./stores/settingsStore";
import { useAgentStore } from "./stores/agentStore";
import { wsService } from "./services/websocket";

// 应用启动时立即连接 Agent WebSocket（引导页试听等功能需要）
function useConnectAgent() {
  const url = useAgentStore((s) => s.url);
  useEffect(() => {
    wsService.connect(url);
  }, [url]);
}

function App() {
  // 启动时连接 Agent WebSocket（引导页试听等功能依赖）
  useConnectAgent();

  const [showChat, setShowChat] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const onboardingComplete = useSettingsStore((s) => s.settings["onboarding.complete"]);
  const [showOnboarding, setShowOnboarding] = useState(!onboardingComplete);

  // 调整窗口大小（自动选择最佳扩展方向）
  const resizeWindow = useCallback(async (width: number, height: number) => {
    try {
      await invoke("resize_window", { width, height, spriteSize: 96 });
    } catch (e) {
      console.warn("resize_window failed:", e);
    }
  }, []);

  // 切换聊天面板
  const toggleChat = useCallback(async () => {
    const next = !showChat;
    setShowChat(next);
    if (next) {
      await resizeWindow(320, 480);
    } else {
      await resizeWindow(120, 160);
    }
  }, [showChat, resizeWindow]);

  // 打开设置
  const openSettings = useCallback(async () => {
    setShowSettings(true);
    await resizeWindow(420, 520);
  }, [resizeWindow]);

  // 关闭设置
  const closeSettings = useCallback(async () => {
    setShowSettings(false);
    if (showChat) {
      await resizeWindow(320, 480);
    } else {
      await resizeWindow(120, 160);
    }
  }, [showChat, resizeWindow]);

  // 监听托盘菜单的 "open-settings" 事件
  useEffect(() => {
    const handler = () => openSettings();
    window.addEventListener("open-settings", handler);
    return () => window.removeEventListener("open-settings", handler);
  }, [openSettings]);

  // 监听 Agent 发来的 "打开设置" 指令
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      if (e.detail === "open-settings") openSettings();
    };
    window.addEventListener("agent-command", handler as EventListener);
    return () => window.removeEventListener("agent-command", handler as EventListener);
  }, [openSettings]);

  // 引导页窗口适配：首次安装时窗口需扩大以容纳引导页
  useEffect(() => {
    if (showOnboarding) {
      resizeWindow(420, 620); // 引导页卡片 420px 宽 + 内边距
    }
  }, [showOnboarding, resizeWindow]);

  // 引导完成
  const handleOnboardingComplete = useCallback(() => {
    setShowOnboarding(false);
    resizeWindow(120, 160); // 引导结束后回到精灵尺寸
  }, [resizeWindow]);

  return (
    <div className="fixed inset-0 overflow-hidden" style={{ background: "transparent" }}>
      {/* 首次引导 */}
      {showOnboarding && <OnboardingWizard onComplete={handleOnboardingComplete} />}

      {/* 聊天面板：固定在精灵上方 */}
      {showChat && (
        <div className="fixed w-80 h-96" style={{ bottom: 140, right: 8, pointerEvents: "auto" }}>
          <ChatPanel />
        </div>
      )}

      {/* 精灵角色：固定在右下角，左键聊天（右键不处理，由系统托盘打开设置） */}
      <div className="fixed" style={{ bottom: 8, right: 8, pointerEvents: "auto" }}>
        <Live2DViewer onClick={toggleChat} />
      </div>

      {/* 设置面板 */}
      {showSettings && <SettingsPanel onClose={closeSettings} />}

      {/* 操作确认弹窗 */}
      <ConfirmDialog />
    </div>
  );
}

export default App;
