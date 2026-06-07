import { invoke } from "@tauri-apps/api/core";

/**
 * 执行 OS 操作能力
 * 通过 Tauri Command 调用 Rust 端的 OS Adapter
 */
export async function executeCapability(request: {
  id: string;
  capability: { type: string; payload?: Record<string, any> };
  context?: { os: string; user: string; session_id: string };
  policy?: { require_confirmation: boolean; risk_score: number; audit: boolean; rollback: boolean };
}): Promise<{
  id: string;
  success: boolean;
  data?: any;
  error?: string;
}> {
  return invoke("execute_capability", { request });
}
