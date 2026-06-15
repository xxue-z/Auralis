import { invoke } from "@tauri-apps/api/core";

const CAPABILITY_TIMEOUT_MS = 25000;

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
  needs_confirmation?: any;
}> {
  const result = await Promise.race([
    invoke("execute_capability", { request }),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("操作执行超时")), CAPABILITY_TIMEOUT_MS)
    ),
  ]);
  return result as any;
}
