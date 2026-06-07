import { create } from "zustand";

export interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  status: "streaming" | "done" | "error";
  timestamp: number;
}

interface ChatState {
  messages: Message[];
  isThinking: boolean;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  appendToMessage: (id: string, content: string) => void;
  setThinking: (thinking: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isThinking: false,
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),
  appendToMessage: (id, content) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + content } : m
      ),
    })),
  setThinking: (thinking) => set({ isThinking: thinking }),
  clearMessages: () => set({ messages: [] }),
}));
