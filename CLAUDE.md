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
├── init/           # 项目立项文件
│   └── v1.0.0/
├── specs/          # 需求规格文档
│   └── v1.0.0/
├── plans/          # 实施计划
│   └── v1.0.0/
├── fix/            # 问题修复归档
│   └── v1.0.0/
├── refine/         # 功能优化归档
│   └── v1.0.0/
└── logo/           # 图标资源
```

---

## 架构

```
UI (Tauri + React 多窗口)
  ↕ WebSocket
Agent Core (Python)
  → MCP Router → Plugin → OS Adapter (Rust) → OS
  → Memory Layer (SQLite + LanceDB)
  → Model Layer (Cloud LLM / Local LLM)
```

### 窗口架构

三个独立的 Tauri WebviewWindow，各有一个独立的 JS 堆：

| 窗口 | 入口 | 用途 |
|------|------|------|
| `pet` | `pet-main.tsx` → `PetApp` | 精灵主窗口，拖拽、点击区、角色渲染 |
| `chat` | `chat-main.tsx` → `ChatApp` | 聊天面板 |
| `settings` | `settings-main.tsx` → `SettingsApp` | 设置面板 |

### 跨窗口通信

`Zustand` 每个窗口独立实例。设置同步通过 Tauri IPC `emit("settings-changed")` / `listen(...)` 实现。

---

## 关键文件职责

| 文件 | 职责 |
|------|------|
| `src/components/Pet/PetApp.tsx` | 精灵主窗口：角色渲染、点击区、拖拽移动、自动穿透轮询、模式切换 |
| `src/components/Chat/ChatPanel.tsx` | 聊天面板：消息列表、输入框、确认按钮 |
| `src/components/Character/Live2DViewer.tsx` | 角色渲染：SVG fallback / Live2D 模型、透明度 |
| `src/components/Character/Live2DModelWrapper.tsx` | Live2D 模型加载、缩放、位置 |
| `src/components/Character/PixiCanvas.tsx` | Pixi.js 透明画布（仅 Live2D 模式） |
| `src/components/Settings/SettingsPanel.tsx` | 设置面板布局：左侧导航 + 右侧内容区 |
| `src/components/Settings/ThemeConfig.tsx` | 外观设置：Live2D 标签页（模型/透明度/点击区）+ 聊天标签页 |
| `src/stores/settingsStore.ts` | 全局设置（Zustand + localStorage 持久化 + IPC 跨窗口同步） |
| `src-tauri/src/tray.rs` | 系统托盘：模式切换子菜单、左键点击 toggle、退出 |
| `src-tauri/capabilities/default.json` | Tauri 权限声明 |

---

## 关键数据流

### 模式系统

三种模式通过 `appearance.mode` 控制：

- **交互模式**（默认）：自动穿透轮询 — 默认 `setIgnoreCursorEvents(true)`（点击穿透），轮询检测鼠标是否进入点击区 → 进入则捕获，`pointerleave` 事件即时恢复穿透
- **专注模式**：始终 `setIgnoreCursorEvents(true)`，所有点击穿透到底层窗口
- **隐藏模式**：`appWindow.hide()`

托盘菜单切换模式 → Rust `on_menu_event` → `window.eval`（`__TAURI_INTERNALS__` + CustomEvent）→ `mode-changed` 事件 → `useSettingsStore.setSetting` → React 响应

### 点击区穿透（交互模式）

```
默认: setIgnoreCursorEvents(true)  ← 点击穿透
  ↓ 轮询 (requestAnimationFrame)
cursorPosition() + outerPosition() 计算鼠标是否在点击区内
  ↓ 进入点击区
setIgnoreCursorEvents(false)  ← 捕获点击
  ↓ pointerleave 事件
setIgnoreCursorEvents(true)   ← 恢复穿透（即时，无需轮询）
```

### 点击精灵打开聊天

```
点击区 pointerUp → openChat
  → WebviewWindow.getByLabel("chat")
  → 已有：show()（首次 setPosition，后续保留用户手动位置）+ setFocus()
  → 无：新建 WebviewWindow
```

### 模型/尺寸渲染

```
settings["appearance.model_id"] 决定模型
spriteSize = model:{id}:sprite_size ?? appearance.sprite_size ?? 96
winSize = spriteSize + 40
Live2DViewer 根据 modelId 选择 SVG / Live2D
```

---

## 窗口启动流程

```mermaid
PetApp mount
  ├─ 恢复存储的窗口位置（localStorage）
  ├─ 预创建 chat 窗口（visible: false）
  ├─ 预创建 settings 窗口（visible: false）
  ├─ 启动穿透轮询（交互模式）
  └─ 监听 agent-command / mode-changed 事件
```

---

## 启动方式

```powershell
# 一键启动
.\scripts\dev.ps1

# 分步
.\scripts\start-agent.ps1   # Python Agent
npm run tauri dev            # Tauri
```

---

## 开发约定

1. **语言**：代码注释、commit message、文档均使用中文
2. **安全**：所有 OS 操作必须经过 Safety Hook + 用户确认
3. **设置**：所有应用设置对 AI 公开，可通过对话修改
4. **国际化**：默认英文，支持中文切换
