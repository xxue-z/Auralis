/**
 * 声音克隆/生成服务
 * 上传音频克隆音色 或 用文字描述生成音线
 */

import { wsService } from "./websocket";

const TIMEOUT_MS = 30000; // 30 秒超时

/**
 * 带超时的 Promise 包装
 */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  return Promise.race([
    promise,
    new Promise<null>((resolve) => setTimeout(() => resolve(null), ms)),
  ]);
}

/**
 * 上传音频克隆音色
 */
export async function cloneVoice(
  audioFile: File,
): Promise<{ voice_id: string; name: string } | null> {
  const promise = new Promise<{ voice_id: string; name: string } | null>((resolve) => {
    const reader = new FileReader();

    reader.onload = async () => {
      const base64 = (reader.result as string).split(",")[1];

      const handler = (data: any) => {
        if (data.type === "voice_clone_result") {
          wsService.off("voice_clone_result", handler);
          resolve(data.success ? { voice_id: data.voice_id, name: data.name } : null);
        }
      };

      wsService.on("voice_clone_result", handler);
      wsService.send({
        type: "voice_clone",
        audio: base64,
        filename: audioFile.name,
      });
    };

    reader.onerror = () => resolve(null);

    try {
      reader.readAsDataURL(audioFile);
    } catch {
      resolve(null);
    }
  });

  return withTimeout(promise, TIMEOUT_MS);
}

/**
 * 试听音线：用指定 preset 合成一段短音频
 */
export async function previewVoice(
  voiceId: string,
): Promise<string | null> {
  // 等待 WebSocket 连接就绪（最多 5s，处理重连中状态）
  const ready = await wsService.waitForConnection(5000);
  if (!ready) {
    console.warn("[Voice] WebSocket 未连接，无法试听");
    return null;
  }

  console.log(`[Voice] 试听请求: voice_id=${voiceId}`);

  const promise = new Promise<string | null>((resolve) => {
    const handler = (data: any) => {
      if (data.type === "voice_preview_result" && data.voice_id === voiceId) {
        wsService.off("voice_preview_result", handler);
        if (data.success && data.audio) {
          console.log(`[Voice] 试听音频收到: ${data.audio.length} chars base64`);
          resolve(data.audio);
        } else {
          console.warn(`[Voice] 试听失败:`, data.error || "无音频数据");
          resolve(null);
        }
      }
    };

    wsService.on("voice_preview_result", handler);
    const sent = wsService.send({
      type: "voice_preview",
      voice_id: voiceId,
    });
    if (!sent) {
      wsService.off("voice_preview_result", handler);
      console.warn("[Voice] 消息发送失败");
      resolve(null);
    }
  });

  return withTimeout(promise, 15000);
}

/**
 * AI 生成音线
 */
export async function generateVoice(
  description: string,
): Promise<{
  voice_id: string;
  name: string;
  description: string;
  matched_features: string[];
  preview_audio: string | null;
} | null> {
  const promise = new Promise<any>((resolve) => {
    const handler = (data: any) => {
      if (data.type === "voice_generate_result") {
        wsService.off("voice_generate_result", handler);
        resolve(data.success ? data : null);
      }
    };

    wsService.on("voice_generate_result", handler);
    wsService.send({
      type: "voice_generate",
      description,
    });
  });

  return withTimeout(promise, TIMEOUT_MS);
}
