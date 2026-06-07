import { create } from "zustand";

export type AgentStatus = "connecting" | "connected" | "disconnected" | "error";
export type PersonaState = "idle" | "speaking" | "thinking" | "happy";

interface AgentState {
  status: AgentStatus;
  url: string;
  personaState: PersonaState;
  setStatus: (status: AgentStatus) => void;
  setUrl: (url: string) => void;
  setPersonaState: (state: PersonaState) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  status: "disconnected",
  url: "ws://127.0.0.1:9527",
  personaState: "idle",
  setStatus: (status) => set({ status }),
  setUrl: (url) => set({ url }),
  setPersonaState: (personaState) => set({ personaState }),
}));
