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
