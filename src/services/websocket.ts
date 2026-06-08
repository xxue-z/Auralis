import { useAgentStore } from "../stores/agentStore";

type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  connect(url: string) {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;

    useAgentStore.getState().setStatus("connecting");
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[WebSocket] Connected to", url);
      useAgentStore.getState().setStatus("connected");
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data.type, data);

        // 更新角色状态
        if ((data.type === "agent_response" || data.type === "agent_audio") && data.persona_state) {
          useAgentStore.getState().setPersonaState(data.persona_state);
        }
      } catch (e) {
        console.error("[WebSocket] Failed to parse message:", e);
      }
    };

    this.ws.onclose = () => {
      console.log("[WebSocket] Disconnected");
      useAgentStore.getState().setStatus("disconnected");
      this.tryReconnect(url);
    };

    this.ws.onerror = (error) => {
      console.error("[WebSocket] Error:", error);
      useAgentStore.getState().setStatus("error");
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  send(data: any): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    } else {
      console.warn("[WebSocket] Not connected, cannot send:", data.type);
      return false;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) handlers.splice(index, 1);
    }
  }

  private emit(type: string, data: any) {
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => handler(data));
    }
  }

  private tryReconnect(url: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => this.connect(url), delay);
  }
}

export const wsService = new WebSocketService();
