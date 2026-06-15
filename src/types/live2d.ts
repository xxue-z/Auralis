/**
 * Live2D 模型类型定义
 */

import type { PersonaState } from "../stores/agentStore";

/** 模型配置 */
export interface Live2DModelConfig {
  /** 唯一标识 */
  id: string;
  /** 显示名称 */
  name: string;
  /** 英文名称 */
  nameEn: string;
  /** model3.json 相对路径 */
  path: string;
  /** 缩略图路径 */
  thumbnail?: string;
  /** 模型来源 */
  type: "bundled" | "imported";
  /** 状态 → motion group 映射 */
  mappings: Record<PersonaState, string>;
  /** 模型文件系统目录（仅 imported 模型） */
  modelDir?: string;
}

/** 模型注册表 */
export interface ModelRegistry {
  models: Live2DModelConfig[];
}
