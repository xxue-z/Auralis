import { create } from "zustand";

export interface PendingConfirmation {
  capability: any;
  message: string;
  riskLevel: string;
  resolve: (confirmed: boolean) => void;
}

interface ConfirmState {
  pending: PendingConfirmation | null;
  showConfirm: (info: PendingConfirmation) => void;
  respond: (confirmed: boolean) => void;
}

export const useConfirmStore = create<ConfirmState>((set) => ({
  pending: null,
  showConfirm: (info) => set({ pending: info }),
  respond: (confirmed) => {
    const pending = useConfirmStore.getState().pending;
    if (pending) {
      pending.resolve(confirmed);
      set({ pending: null });
    }
  },
}));
