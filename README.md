# Auralis — 桌面精灵操作系统智能体

> 常驻桌面的人格化 OS 控制层 Agent，用自然语言安全操作电脑。

[English](README_en.md) | **中文**

---

## 项目简介

Auralis 是一个常驻桌面的智能助手，通过自然语言与用户交互，安全地执行操作系统级任务。它不是一个简单的聊天机器人，而是一个真正能操作电脑的 AI Agent。

### 核心特性

- 🧚 **桌面精灵**：可爱的 SVG 角色常驻桌面，支持待机、说话、思考、开心四种动画状态
- 💬 **自然语言对话**：支持中英文，接入云端/本地 LLM，理解复杂指令
- 🔧 **系统操作**：文件管理、应用控制、系统信息查询、剪贴板操作
- 🛡️ **安全策略**：风险评估、权限控制、用户确认、审计日志
- 🧠 **记忆系统**：记住用户偏好、操作历史、实体关系
- 🎭 **人格系统**：4 维度性格参数（幽默/详细/主动/精确），影响 Agent 行为
- 🔌 **MCP 插件**：可扩展的插件架构，支持热插拔

### 用户体验

| 场景 | 体验 |
|------|------|
| "帮我清理桌面垃圾文件" | Agent 扫描文件 → 分类 → 展示报告 → 用户确认 → 执行清理 |
| "打开 Chrome 并访问 GitHub" | Agent 启动应用 → 打开指定网址 |
| "我的项目都在哪个目录？" | Agent 从记忆中检索 → 告诉你 D:\Project |
| "把语言改成中文" | Agent 修改设置 → 界面切换语言 |
| "我通常周五下午清理下载目录" | Agent 记住习惯 → 下周五主动提醒 |

---

## 技术架构

```
┌─────────────────────────────────────────────┐
│              UI Layer (React + TypeScript)   │
│  ChatPanel │ Settings │ Live2D │ Onboarding  │
└───────────────────┬─────────────────────────┘
                    │ WebSocket
┌───────────────────▼─────────────────────────┐
│           Agent Core (Python)                │
│  LLM │ Memory │ Policy │ MCP │ Planner      │
└───────────────────┬─────────────────────────┘
                    │ Tauri IPC
┌───────────────────▼─────────────────────────┐
│         OS Adapter Layer (Rust)              │
│  File │ App │ System │ UI Automation         │
└─────────────────────────────────────────────┘
```

详细架构设计请参考：[.docs/specs/v1.0.0/ARCHITECTURE.md](.docs/specs/v1.0.0/ARCHITECTURE.md)

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Tauri 2.0 + React + TypeScript | 桌面应用框架 |
| **后端** | Rust (Tauri) | 系统级操作、OS Adapter |
| **Agent** | Python 3.11+ | AI 逻辑、LLM 集成、记忆、插件 |
| **通信** | WebSocket | 前端 ↔ Agent 双向通信 |
| **存储** | SQLite + JSON | 对话、审计、记忆持久化 |
| **本地模型** | Ollama | 可选的本地 LLM 推理 |

---

## 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Node.js | ≥ 18 | 前端构建 |
| Rust | ≥ 1.70 | Tauri 后端编译 |
| Python | ≥ 3.11 | Agent Core |
| Ollama | 最新版 | 可选，本地模型推理 |

---

## 快速开始

### 方式一：一键启动（推荐）

```powershell
# PowerShell
.\scripts\dev.ps1

# 或双击 start.bat
```

### 方式二：分步启动

```powershell
# 终端 1：启动 Python Agent
cd agent
pip install -r requirements.txt
python server.py

# 终端 2：启动 Tauri 前端
npm install
npm run tauri dev
```

---

## 编译与打包

### 开发模式

```bash
npm run tauri dev
```

### 生产构建

```bash
npm run tauri build
```

构建产物位于 `src-tauri/target/release/bundle/`。

### 安装包

构建完成后会生成：
- **Windows**: `.msi` 安装包
- **macOS**: `.app` 应用包
- **Linux**: `.deb` / `.AppImage`

---

## 项目结构

```
Auralis/
├── src/                    # 前端源码 (React + TypeScript)
│   ├── components/         # UI 组件
│   │   ├── Character/      # Live2D 角色
│   │   ├── Chat/           # 聊天面板
│   │   ├── Settings/       # 设置面板
│   │   └── Onboarding/     # 引导流程
│   ├── stores/             # 状态管理
│   ├── services/           # WebSocket、音频等服务
│   └── i18n/               # 国际化
│
├── src-tauri/              # Rust 后端
│   └── src/
│       └── os_adapter/     # OS 操作适配器
│           ├── capability.rs   # 能力协议
│           ├── safety.rs       # 安全策略
│           └── windows/        # Windows 实现
│               ├── file.rs     # 文件操作
│               ├── app.rs      # 应用管理
│               ├── system.rs   # 系统操作
│               └── ui.rs       # UI 自动化
│
├── agent/                  # Python Agent Core
│   ├── server.py           # WebSocket 服务端
│   ├── model/              # LLM 接口（云端/本地）
│   ├── memory/             # 记忆系统
│   ├── policy/             # 安全策略
│   ├── mcp/                # MCP 插件系统
│   ├── planner/            # 任务规划
│   └── persona/            # 人格系统
│
├── plugins/                # MCP 插件
│   ├── file.mcp/           # 文件操作插件
│   ├── app.mcp/            # 应用管理插件
│   └── system.mcp/         # 系统操作插件
│
├── .docs/                  # 项目文档
│   ├── specs/              # 需求规格
│   ├── plans/              # 实施计划
│   └── init/               # 立项文档
│
└── scripts/                # 启动脚本
```

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 项目开发规范 |
| [.docs/specs/v1.0.0/PRD.md](.docs/specs/v1.0.0/PRD.md) | 产品需求文档 |
| [.docs/specs/v1.0.0/ARCHITECTURE.md](.docs/specs/v1.0.0/ARCHITECTURE.md) | 系统架构设计 |
| [.docs/specs/v1.0.0/OS-ADAPTER-SPEC.md](.docs/specs/v1.0.0/OS-ADAPTER-SPEC.md) | OS Adapter 规格 |
| [.docs/specs/v1.0.0/MCP-PROTOCOL-SPEC.md](.docs/specs/v1.0.0/MCP-PROTOCOL-SPEC.md) | MCP 协议规格 |
| [.docs/specs/v1.0.0/PERSONA-MEMORY-SPEC.md](.docs/specs/v1.0.0/PERSONA-MEMORY-SPEC.md) | 人格与记忆规格 |
| [.docs/specs/v1.0.0/I18N-SETTINGS-SPEC.md](.docs/specs/v1.0.0/I18N-SETTINGS-SPEC.md) | 国际化与设置规格 |
| [.docs/specs/v1.0.0/MODEL-CONFIG-SPEC.md](.docs/specs/v1.0.0/MODEL-CONFIG-SPEC.md) | 模型配置规格 |
| [.docs/specs/v1.0.0/DEVELOPMENT-ROADMAP.md](.docs/specs/v1.0.0/DEVELOPMENT-ROADMAP.md) | 开发路线图 |
| [README_MCP.md](README_MCP.md) | MCP 插件开发手册 |

---

## 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| LLM 接入 | ✅ | 云端/本地模型自动切换 |
| Function Calling | ✅ | 13 种 Capability 支持 |
| DAG Planner | ✅ | 复杂任务拆解与并行执行 |
| 三层记忆 | ✅ | Event + Semantic + Graph |
| Policy & Safety | ✅ | 风险评估 + 权限控制 |
| MCP 插件系统 | ✅ | 协议层 + 加载器 + 3 个插件 |
| 人格系统 | ✅ | 4 维度性格参数 |
| 行为策略 | ✅ | 性格影响 Agent 行为 |
| Live2D 角色 | ✅ | SVG 动画精灵 |
| UI Automation | ✅ | 点击/输入/截图 |
| 国际化 | ✅ | 中英文支持 |
| 本地模型 | ✅ | Ollama 集成 |

---

## 测试

```bash
cd agent
python -m pytest test_*.py -v
```

当前共 **268** 个单元测试全部通过。

---

## 开发约定

1. **语言**：代码注释、commit message、文档均使用中文
2. **安全**：所有 OS 操作必须经过 Safety Hook + 用户确认
3. **测试**：新功能必须包含单元测试
4. **审查**：每次提交前进行代码审查和用户视角审查

---

## 许可证

MIT License
