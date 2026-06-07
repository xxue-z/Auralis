# Auralis — 桌面精灵操作系统智能体

> 常驻桌面的人格化 OS 控制层 Agent，用自然语言安全操作电脑。

---

## 项目信息

| 项 | 值 |
|---|---|
| 项目名称 | Auralis |
| 当前版本 | v1.0.0 |
| 技术栈 | Tauri 2.0 (Rust + React) + Python Agent Core |
| 目标平台 | Windows 优先，macOS / Linux 后续 |
| 本地模型 | Qwen 2.5-1.5B / Phi-3-mini（可选） |

---

## 文档规范

所有项目文档存放在 `.docs/` 目录下，按用途分类，每个分类内按版本号创建子文件夹。

### 目录结构

```
.docs/
├── init/           # 项目立项文件（初始需求、可行性分析、问题记录）
│   └── v1.0.0/     # v1.0.0 版本的立项文档
│
├── specs/          # 项目需求规格文档（PRD、架构设计、技术规格）
│   └── v1.0.0/     # v1.0.0 版本的需求文档
│
├── plans/          # 项目实施计划（开发路线图、里程碑、任务拆解）
│   └── v1.0.0/     # v1.0.0 版本的实施计划
│
├── fix/            # 问题修复归档（Bug 修复记录、问题分析）
│   └── v1.0.0/     # v1.0.0 版本的修复记录
│
├── refine/         # 功能优化归档（优化方案、重构记录）
│   └── v1.0.0/     # v1.0.0 版本的优化记录
│
└── logo/           # 项目图标资源（不按版本分子文件夹）
```

### 文档命名规范

- 文件名使用中文或英文均可，保持可读性
- 同一功能的文档用相同前缀，如 `OS-ADAPTER-SPEC.md`、`OS-ADAPTER-PLAN.md`
- 修复和优化文档建议格式：`YYYY-MM-DD-简要描述.md`

### 版本文件夹规则

- 写入文档时，根据当前项目版本创建对应版本文件夹
- 当前版本：**v1.0.0**
- 文档路径示例：`.docs/specs/v1.0.0/PRD.md`

---

## 当前版本文档清单（v1.0.0）

### init/v1.0.0/ — 立项文档

| 文件 | 说明 |
|------|------|
| 初版PRD V0.0.1.md | 初版产品需求文档 |
| OS Adapter 总体实现计划.md | OS Adapter 实现方案 |
| MCP 插件版 OS Adapter.md | MCP 插件化架构设计 |
| Auralis MCP Schema 标准 v1.0.md | MCP 协议标准 |
| 问题.txt | 待解决问题清单 |

### specs/v1.0.0/ — 需求规格

| 文件 | 说明 |
|------|------|
| PRD.md | 产品需求文档（P0/P1/P2 功能分级） |
| ARCHITECTURE.md | 系统架构设计（7 层架构、技术栈、数据流） |
| OS-ADAPTER-SPEC.md | OS Adapter 技术规格（Capability 协议、安全钩子） |
| MCP-PROTOCOL-SPEC.md | MCP 协议规格（Schema、插件标准、Router） |
| PERSONA-MEMORY-SPEC.md | 人格与记忆系统规格（Persona、Nexus Memory） |
| I18N-SETTINGS-SPEC.md | 国际化与 AI 可控设置系统规格 |
| DEVELOPMENT-ROADMAP.md | 开发路线图（4 阶段 × 4 周、任务拆解） |

---

## 架构要点

```
UI (Tauri + React)
  ↕ WebSocket
Agent Core (Python)
  → MCP Router → Plugin → OS Adapter (Rust) → OS
  → Memory Layer (SQLite + LanceDB)
  → Model Layer (Cloud LLM / Local LLM)
```

- **Rust**：系统层操作（文件、应用、系统），运行在 Tauri 后端
- **Python**：AI 逻辑（意图识别、任务规划、LLM 调用、记忆、人格）
- **前端**：React + TypeScript，Live2D 角色，聊天 UI

---

## 启动方式

### 一键启动（推荐）

```powershell
# 方式一：PowerShell
.\scripts\dev.ps1

# 方式二：双击 start.bat
```

### 分步启动

```powershell
# 终端 1：启动 Python Agent
.\scripts\start-agent.ps1

# 终端 2：启动 Tauri
npm run tauri dev
```

---

## 开发约定

1. **语言**：代码注释、commit message、文档均使用中文
2. **安全**：所有 OS 操作必须经过 Safety Hook + 用户确认
3. **设置**：所有应用设置对 AI 公开，可通过对话修改
4. **国际化**：默认英文，支持中文切换，AI 回复跟随用户语言设置
