import { useEffect, useCallback } from "react";
import { wsService } from "../services/websocket";
import { executeCapability } from "../services/tauri-api";
import { playAudio } from "../services/audio";
import { useAgentStore } from "../stores/agentStore";
import { useChatStore } from "../stores/chatStore";
import { useConfirmStore } from "../stores/confirmStore";
import { useSettingsStore } from "../stores/settingsStore";

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
}

export function useAgent() {
  const url = useAgentStore((s) => s.url);
  const addMessage = useChatStore((s) => s.addMessage);
  const updateMessage = useChatStore((s) => s.updateMessage);
  const appendToMessage = useChatStore((s) => s.appendToMessage);
  const setThinking = useChatStore((s) => s.setThinking);

  useEffect(() => {
    // 处理 Agent 的文本回复
    const handleAgentResponse = (data: any) => {
      if (data.status === "streaming") {
        const messages = useChatStore.getState().messages;
        const lastAgentMsg = messages.filter((m) => m.role === "agent").pop();
        if (lastAgentMsg && lastAgentMsg.status === "streaming") {
          if (lastAgentMsg.id === data.id) {
            appendToMessage(lastAgentMsg.id, data.content);
          } else {
            // 同一 message_id 被多次调用时，ID 不同（UUID 后缀），视为新消息
            addMessage({
              id: data.id || generateId(),
              role: "agent",
              content: data.content,
              status: "streaming",
              timestamp: Date.now(),
            });
          }
        } else {
          // 检查是否已有相同 ID 的消息（防重复）
          const existing = messages.find((m) => m.id === data.id);
          if (existing) return;
          addMessage({
            id: data.id || generateId(),
            role: "agent",
            content: data.content,
            status: "streaming",
            timestamp: Date.now(),
          });
        }
        setThinking(false);
      } else if (data.status === "done") {
        const messages = useChatStore.getState().messages;
        const agentMsg = messages.filter((m) => m.role === "agent").find((m) => m.id === data.id) || messages.filter((m) => m.role === "agent").pop();
        if (agentMsg) {
          updateMessage(agentMsg.id, { status: "done" });
        }
      } else if (data.status === "error") {
        const messages = useChatStore.getState().messages;
        const existing = messages.find((m) => m.id === data.id);
        if (existing) return;
        addMessage({
          id: data.id || generateId(),
          role: "agent",
          content: data.content || "发生错误",
          status: "error",
          timestamp: Date.now(),
        });
        setThinking(false);
      }
    };

    // 执行单个 capability，处理确认流程
    const executeWithConfirm = async (cap: any): Promise<any> => {
      const result = await executeCapability(cap);

      // 如果需要确认，弹出确认对话框
      if (result.needs_confirmation) {
        const confirmed = await new Promise<boolean>((resolve) => {
          useConfirmStore.getState().showConfirm({
            capability: cap,
            message: result.needs_confirmation.message,
            riskLevel: result.needs_confirmation.risk_level,
            resolve,
          });
        });

        if (confirmed) {
          // 用户确认，重新执行（带 confirmed 标记）
          return executeCapability({
            ...cap,
            policy: { require_confirmation: true, risk_score: 0, audit: true, rollback: true },
          });
        } else {
          // 用户取消
          return { id: cap.id, success: false, error: "用户取消操作" };
        }
      }

      return result;
    };

    // 处理 Agent 的 OS 能力执行请求
    const handleCapabilityRequest = async (data: any) => {
      const capabilities = data.capabilities || [];
      const requestId = data.request_id;
      const results: any[] = [];

      for (const cap of capabilities) {
        try {
          const capWithContext = {
            ...cap,
            context: cap.context || { os: "windows", user: "default", session_id: "default" },
          };
          const result = await executeWithConfirm(capWithContext);
          results.push(result);
        } catch (err: any) {
          results.push({
            id: cap.id,
            success: false,
            error: err.toString(),
          });
        }
      }

      // 把执行结果发回 Agent
      wsService.send({
        type: "capability_result",
        request_id: requestId,
        results,
      });
    };

    // 处理 Agent 的设置查询请求
    const handleSettingsQuery = (data: any) => {
      const requestId = data.request_id;
      const allSettings = useSettingsStore.getState().getAllSettings();
      wsService.send({
        type: "settings_query_result",
        request_id: requestId,
        settings: allSettings,
      });
    };

    // 处理 Agent 的设置修改请求
    const handleSettingsChange = (data: any) => {
      const requestId = data.request_id;
      const changes = data.changes || [];
      const store = useSettingsStore.getState();

      const results: any[] = [];
      for (const change of changes) {
        try {
          let finalValue = change.value;

          // 处理 "increase"/"decrease"（数值类设置微调，范围从默认值推断）
          if (finalValue === "increase" || finalValue === "decrease") {
            const current = store.getSetting(change.key);
            if (typeof current === "number") {
              const delta = finalValue === "increase" ? 0.1 : -0.1;
              // 根据设置类型确定范围
              let min = 0.0, max = 1.0;
              if (change.key.includes("speed") || change.key.includes("pitch")) {
                min = 0.5; max = 2.0;
              } else if (change.key.includes("size")) {
                min = 64; max = 200;
              } else if (change.key.includes("opacity")) {
                min = 0.3; max = 1.0;
              }
              finalValue = Math.min(max, Math.max(min, Math.round((current + delta) * 10) / 10));
            }
          }

          store.setSetting(change.key, finalValue);
          results.push({ key: change.key, success: true, value: finalValue });
        } catch (err: any) {
          results.push({ key: change.key, success: false, error: err.toString() });
        }
      }

      wsService.send({
        type: "settings_change_result",
        request_id: requestId,
        results,
      });
    };

    // 处理 Agent 发来的指令（如打开设置）
    const handleAgentCommand = (data: any) => {
      const command = data.command;
      if (command === "open-settings") {
        window.dispatchEvent(new CustomEvent("agent-command", { detail: "open-settings" }));
      }
    };

    // 处理 Agent 发来的音频
    const handleAgentAudio = (data: any) => {
      if (data.audio) {
        playAudio(data.audio);
      }
    };

    // 处理 Agent 角色状态更新（独立事件，不影响消息列表）
    const handlePersonaUpdate = (data: any) => {
      if (data.persona_state) {
        useAgentStore.getState().setPersonaState(data.persona_state);
      }
    };

    wsService.on("agent_response", handleAgentResponse);
    wsService.on("capability_request", handleCapabilityRequest);
    wsService.on("settings_query", handleSettingsQuery);
    wsService.on("settings_change", handleSettingsChange);
    wsService.on("agent_command", handleAgentCommand);
    wsService.on("agent_audio", handleAgentAudio);
    wsService.on("persona_update", handlePersonaUpdate);

    return () => {
      wsService.off("agent_response", handleAgentResponse);
      wsService.off("capability_request", handleCapabilityRequest);
      wsService.off("settings_query", handleSettingsQuery);
      wsService.off("settings_change", handleSettingsChange);
      wsService.off("agent_command", handleAgentCommand);
      wsService.off("agent_audio", handleAgentAudio);
      wsService.off("persona_update", handlePersonaUpdate);
    };
  }, [addMessage, updateMessage, appendToMessage, setThinking]);

  const sendMessage = useCallback((content: string) => {
    const messageId = generateId();
    addMessage({
      id: messageId,
      role: "user",
      content,
      status: "done",
      timestamp: Date.now(),
    });
    setThinking(true);
    // 设置角色为思考状态
    useAgentStore.getState().setPersonaState("thinking");
    wsService.send({
      type: "user_message",
      id: messageId,
      content,
      mode: "text",
      session_id: "default",
    });
  }, [addMessage, setThinking]);

  const connect = useCallback(() => {
    wsService.connect(url);
  }, [url]);

  const disconnect = useCallback(() => {
    wsService.disconnect();
  }, []);

  // 连接成功后同步设置到 Agent
  useEffect(() => {
    const handleConnect = () => {
      const allSettings = useSettingsStore.getState().getAllSettings();
      wsService.send({
        type: "settings_update",
        settings: allSettings,
      });
    };
    const unsubscribe = useAgentStore.subscribe((state) => {
      if (state.status === "connected") handleConnect();
    });
    return unsubscribe; // 清理订阅
  }, []);

  return { sendMessage, connect, disconnect };
}
