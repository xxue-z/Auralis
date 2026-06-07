import { useEffect, useCallback } from "react";
import { wsService } from "../services/websocket";
import { executeCapability } from "../services/tauri-api";
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
          appendToMessage(lastAgentMsg.id, data.content);
        } else {
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
        const lastAgentMsg = messages.filter((m) => m.role === "agent").pop();
        if (lastAgentMsg) {
          updateMessage(lastAgentMsg.id, { status: "done" });
        }
      } else if (data.status === "error") {
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
          const result = await executeWithConfirm(cap);
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

          // 处理 "increase"/"decrease"（数值类设置微调）
          if (finalValue === "increase" || finalValue === "decrease") {
            const current = store.getSetting(change.key);
            if (typeof current === "number") {
              const delta = finalValue === "increase" ? 0.1 : -0.1;
              finalValue = Math.min(1.0, Math.max(0.0, Math.round((current + delta) * 10) / 10));
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

    wsService.on("agent_response", handleAgentResponse);
    wsService.on("capability_request", handleCapabilityRequest);
    wsService.on("settings_query", handleSettingsQuery);
    wsService.on("settings_change", handleSettingsChange);

    return () => {
      wsService.off("agent_response", handleAgentResponse);
      wsService.off("capability_request", handleCapabilityRequest);
      wsService.off("settings_query", handleSettingsQuery);
      wsService.off("settings_change", handleSettingsChange);
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

  return { sendMessage, connect, disconnect };
}
