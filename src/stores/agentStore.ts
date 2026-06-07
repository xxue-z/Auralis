import { create } from "zustand";

export type AgentStatus = "connecting" | "connected" | "disconnected" | "error";

interface AgentState {
  status: AgentStatus;
  url: string;
  setStatus: (status: AgentStatus) => void;
  setUrl: (url: string) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  status: "disconnected",
  url: "ws://127.0.0.1:9527",
  setStatus: (status) => set({ status }),
  setUrl: (url) => set({ url }),
}));
