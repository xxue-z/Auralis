/**
 * 云端厂商列表服务
 * 从远程 CDN 拉取厂商列表，支持本地缓存和用户自定义
 */

export interface Vendor {
  vendor: string;
  description: string;
  supported_modes: string[];
  base_urls: Record<string, string>;
  key_url: string;
  models: string[];
}

const CDN_URL =
  "https://cdn.jsdelivr.net/gh/xxue-z/Knode@master/.resource/cloud_models.json";
const CACHE_KEY = "auralis-cloud-vendors-cache";
const CUSTOM_KEY = "auralis-custom-vendors";

/**
 * 拉取远程厂商列表（带缓存降级）
 */
export async function fetchVendors(): Promise<Vendor[]> {
  try {
    const res = await fetch(CDN_URL, {
      signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const vendors: Vendor[] = data.vendors || [];
    // 更新缓存
    localStorage.setItem(CACHE_KEY, JSON.stringify(vendors));
    return [...vendors, ...getCustomVendors()];
  } catch {
    // 降级到缓存
    return [...getCachedVendors(), ...getCustomVendors()];
  }
}

/**
 * 读取本地缓存的厂商列表
 */
export function getCachedVendors(): Vendor[] {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) return JSON.parse(cached);
  } catch {}
  return [];
}

/**
 * 获取用户自定义厂商
 */
export function getCustomVendors(): Vendor[] {
  try {
    const custom = localStorage.getItem(CUSTOM_KEY);
    if (custom) return JSON.parse(custom);
  } catch {}
  return [];
}

/**
 * 保存用户自定义厂商
 */
export function saveCustomVendor(vendor: Vendor): void {
  const customs = getCustomVendors();
  const existing = customs.findIndex((v) => v.vendor === vendor.vendor);
  if (existing >= 0) {
    customs[existing] = vendor;
  } else {
    customs.push(vendor);
  }
  localStorage.setItem(CUSTOM_KEY, JSON.stringify(customs));
}

/**
 * 删除用户自定义厂商
 */
export function deleteCustomVendor(vendorName: string): void {
  const customs = getCustomVendors().filter((v) => v.vendor !== vendorName);
  localStorage.setItem(CUSTOM_KEY, JSON.stringify(customs));
}
