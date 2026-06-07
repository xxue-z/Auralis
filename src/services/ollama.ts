/**
 * Ollama 状态检测服务
 * 检测 Ollama 是否运行，获取已下载的模型列表
 */

export interface OllamaModel {
  name: string;
  size: number;
  modified: string;
}

/**
 * 检测 Ollama 是否运行
 */
export async function checkOllamaStatus(baseUrl: string): Promise<boolean> {
  try {
    // 将 /v1 去掉，用 /api/tags 检测
    const apiUrl = baseUrl.replace(/\/v1\/?$/, "");
    const res = await fetch(`${apiUrl}/api/tags`, {
      method: "GET",
      signal: AbortSignal.timeout(3000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * 获取 Ollama 已下载的模型列表
 */
export async function listOllamaModels(baseUrl: string): Promise<OllamaModel[]> {
  try {
    const apiUrl = baseUrl.replace(/\/v1\/?$/, "");
    const res = await fetch(`${apiUrl}/api/tags`, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.models || []).map((m: any) => ({
      name: m.name,
      size: m.size,
      modified: m.modified_at,
    }));
  } catch {
    return [];
  }
}
