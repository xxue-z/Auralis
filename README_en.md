# Auralis — Desktop Fairy OS Agent

> A personalized OS control layer Agent that lives on your desktop, operating your computer with natural language.

**English** | [中文](README.md)

---

## Introduction

Auralis is an intelligent desktop assistant that interacts with users through natural language and securely executes operating system-level tasks. It's not just a chatbot — it's a real AI Agent that can operate your computer.

### Key Features

- 🧚 **Desktop Fairy**: A cute SVG character that lives on your desktop with 4 animation states (idle, speaking, thinking, happy)
- 💬 **Natural Language Chat**: Supports Chinese and English, connects to cloud/local LLMs, understands complex commands
- 🔧 **System Operations**: File management, app control, system info, clipboard operations
- 🛡️ **Security Policy**: Risk assessment, permission control, user confirmation, audit logging
- 🧠 **Memory System**: Remembers user preferences, operation history, entity relationships
- 🎭 **Persona System**: 4 personality dimensions (humor/verbosity/proactive/precision) that influence agent behavior
- 🔌 **MCP Plugins**: Extensible plugin architecture with hot-plugging support

### User Experience

| Scenario | Experience |
|----------|------------|
| "Clean up my desktop trash files" | Agent scans files → categorizes → shows report → user confirms → executes cleanup |
| "Open Chrome and go to GitHub" | Agent launches app → opens specified URL |
| "Where are my project files?" | Agent retrieves from memory → tells you D:\Project |
| "Change language to Chinese" | Agent modifies settings → interface switches language |
| "I usually clean downloads on Friday afternoon" | Agent remembers habit → reminds you next Friday |

---

## Architecture

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

For detailed architecture design, see: [.docs/specs/v1.0.0/ARCHITECTURE.md](.docs/specs/v1.0.0/ARCHITECTURE.md)

---

## Tech Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| **Frontend** | Tauri 2.0 + React + TypeScript | Desktop app framework |
| **Backend** | Rust (Tauri) | System-level operations, OS Adapter |
| **Agent** | Python 3.11+ | AI logic, LLM integration, memory, plugins |
| **Communication** | WebSocket | Bidirectional frontend ↔ agent communication |
| **Storage** | SQLite + JSON | Conversation, audit, memory persistence |
| **Local Model** | Ollama | Optional local LLM inference |

---

## Requirements

| Dependency | Version | Description |
|------------|---------|-------------|
| Node.js | ≥ 18 | Frontend build |
| Rust | ≥ 1.70 | Tauri backend compilation |
| Python | ≥ 3.11 | Agent Core |
| Ollama | Latest | Optional, local model inference |

---

## Quick Start

### Option One: One-Click Launch (Recommended)

```powershell
# PowerShell
.\scripts\dev.ps1

# Or double-click start.bat
```

### Option Two: Step-by-Step

```powershell
# Terminal 1: Start Python Agent
cd agent
pip install -r requirements.txt
python server.py

# Terminal 2: Start Tauri Frontend
npm install
npm run tauri dev
```

---

## Build & Package

### Development Mode

```bash
npm run tauri dev
```

### Production Build

```bash
npm run tauri build
```

Build artifacts are located at `src-tauri/target/release/bundle/`.

### Installers

After building, you'll get:
- **Windows**: `.msi` installer
- **macOS**: `.app` application bundle
- **Linux**: `.deb` / `.AppImage`

---

## Project Structure

```
Auralis/
├── src/                    # Frontend source (React + TypeScript)
│   ├── components/         # UI components
│   │   ├── Character/      # Live2D character
│   │   ├── Chat/           # Chat panel
│   │   ├── Settings/       # Settings panel
│   │   └── Onboarding/     # Onboarding flow
│   ├── stores/             # State management
│   ├── services/           # WebSocket, audio services
│   └── i18n/               # Internationalization
│
├── src-tauri/              # Rust backend
│   └── src/
│       └── os_adapter/     # OS operation adapter
│           ├── capability.rs   # Capability protocol
│           ├── safety.rs       # Safety policy
│           └── windows/        # Windows implementation
│               ├── file.rs     # File operations
│               ├── app.rs      # App management
│               ├── system.rs   # System operations
│               └── ui.rs       # UI automation
│
├── agent/                  # Python Agent Core
│   ├── server.py           # WebSocket server
│   ├── model/              # LLM interfaces (cloud/local)
│   ├── memory/             # Memory system
│   ├── policy/             # Security policy
│   ├── mcp/                # MCP plugin system
│   ├── planner/            # Task planning
│   └── persona/            # Persona system
│
├── plugins/                # MCP plugins
│   ├── file.mcp/           # File operations plugin
│   ├── app.mcp/            # App management plugin
│   └── system.mcp/         # System operations plugin
│
├── .docs/                  # Project documentation
│   ├── specs/              # Specifications
│   ├── plans/              # Implementation plans
│   └── init/               # Project initialization docs
│
└── scripts/                # Launch scripts
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Project development conventions |
| [.docs/specs/v1.0.0/PRD.md](.docs/specs/v1.0.0/PRD.md) | Product Requirements Document |
| [.docs/specs/v1.0.0/ARCHITECTURE.md](.docs/specs/v1.0.0/ARCHITECTURE.md) | System Architecture Design |
| [.docs/specs/v1.0.0/OS-ADAPTER-SPEC.md](.docs/specs/v1.0.0/OS-ADAPTER-SPEC.md) | OS Adapter Specification |
| [.docs/specs/v1.0.0/MCP-PROTOCOL-SPEC.md](.docs/specs/v1.0.0/MCP-PROTOCOL-SPEC.md) | MCP Protocol Specification |
| [.docs/specs/v1.0.0/PERSONA-MEMORY-SPEC.md](.docs/specs/v1.0.0/PERSONA-MEMORY-SPEC.md) | Persona & Memory Specification |
| [.docs/specs/v1.0.0/I18N-SETTINGS-SPEC.md](.docs/specs/v1.0.0/I18N-SETTINGS-SPEC.md) | I18N & Settings Specification |
| [.docs/specs/v1.0.0/MODEL-CONFIG-SPEC.md](.docs/specs/v1.0.0/MODEL-CONFIG-SPEC.md) | Model Configuration Specification |
| [.docs/specs/v1.0.0/DEVELOPMENT-ROADMAP.md](.docs/specs/v1.0.0/DEVELOPMENT-ROADMAP.md) | Development Roadmap |
| [README_MCP.md](README_MCP.md) | MCP Plugin Development Guide |

---

## Feature Modules

| Module | Status | Description |
|--------|--------|-------------|
| LLM Integration | ✅ | Cloud/local model auto-switching |
| Function Calling | ✅ | 13 Capability types supported |
| DAG Planner | ✅ | Complex task decomposition & parallel execution |
| Three-Layer Memory | ✅ | Event + Semantic + Graph |
| Policy & Safety | ✅ | Risk assessment + permission control |
| MCP Plugin System | ✅ | Protocol layer + loader + 3 plugins |
| Persona System | ✅ | 4 personality dimensions |
| Behavior Strategy | ✅ | Personality influences agent behavior |
| Live2D Character | ✅ | SVG animated fairy |
| UI Automation | ✅ | Click/type/screenshot |
| Internationalization | ✅ | Chinese/English support |
| Local Model | ✅ | Ollama integration |

---

## Testing

```bash
cd agent
python -m pytest test_*.py -v
```

Currently **268** unit tests all passing.

---

## Development Conventions

1. **Language**: Code comments, commit messages, and documentation in Chinese
2. **Safety**: All OS operations must go through Safety Hook + user confirmation
3. **Testing**: New features must include unit tests
4. **Review**: Code review and user perspective review before each commit

---

## License

This project uses the [Personal Learning & Non-Commercial Use License](LICENSE).

- ✅ Personal learning and research
- ✅ Personal non-commercial use
- ❌ Commercial use (requires authorization)
- ❌ Redistribution

For commercial licensing inquiries, please contact the author.
