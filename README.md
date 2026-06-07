# Auralis — MCP 插件开发手册

> **[English](#english-documentation)** | **中文**（默认）

[返回项目介绍](CLAUDE.md) | [查看项目架构](.docs/specs/v1.0.0/ARCHITECTURE.md) | [查看 MCP 协议规格](.docs/specs/v1.0.0/MCP-PROTOCOL-SPEC.md)

---

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [插件结构](#插件结构)
- [插件 API](#插件-api)
- [生命周期钩子](#生命周期钩子)
- [内置插件](#内置插件)
- [创建自定义插件](#创建自定义插件)
- [插件注册与加载](#插件注册与加载)
- [MCP 协议](#mcp-协议)
- [安全策略](#安全策略)
- [测试插件](#测试插件)
- [常见问题](#常见问题)

---

## 概述

Auralis 的 MCP（Model Capability Protocol）插件系统允许开发者通过 Python 模块扩展 Agent 的能力。插件可以：

- 注册新的 Capability（如 `file.search`、`web.scrape`）
- 通过标准化接口接收和执行请求
- 参与安全策略和审计日志
- 支持热插拔（运行时加载/卸载）

### 架构概览

```
用户输入 → LLM → Tool Call → ToolRouter → MCP Router → Plugin.execute() → 结果返回
                                     ↓
                              Policy Engine（风险评估）
                                     ↓
                              Audit Logger（审计日志）
```

---

## 快速开始

### 1. 创建插件目录

```bash
mkdir plugins/my.mcp
```

### 2. 创建 plugin.json

```json
{
  "name": "my.mcp",
  "version": "1.0.0",
  "description": "我的自定义插件",
  "author": "Your Name",
  "capabilities": ["my.action1", "my.action2"]
}
```

### 3. 创建 plugin.py

```python
"""my.mcp — 自定义插件"""

from mcp.schema import MCPRequest, MCPResponse


async def execute(request: MCPRequest) -> MCPResponse:
    """执行插件操作"""
    action = request.capability.action
    input_data = request.input

    if action == "action1":
        # 实现你的逻辑
        result = {"message": f"处理了: {input_data}"}
        return MCPResponse.success(request.id, result)

    return MCPResponse.make_error(
        request.id, "UNSUPPORTED_ACTION", f"不支持的操作: {action}"
    )
```

### 4. 重启 Agent

插件会在 Agent 启动时自动加载。

---

## 插件结构

```
plugins/
├── my.mcp/
│   ├── plugin.json      # 插件元信息（必需）
│   ├── plugin.py        # 插件入口（必需）
│   └── utils.py         # 可选：辅助函数
```

### plugin.json 字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 插件唯一名称（如 `file.mcp`） |
| `version` | string | ✅ | 语义化版本号 |
| `description` | string | ❌ | 插件描述 |
| `author` | string | ❌ | 作者信息 |
| `capabilities` | string[] | ✅ | 支持的能力列表 |
| `entry` | string | ❌ | 入口文件名（默认 `plugin`） |

### 能力命名规范

能力名称格式：`{namespace}.{action}`

| 命名空间 | 用途 | 示例 |
|---------|------|------|
| `file` | 文件操作 | `file.read`, `file.write`, `file.delete` |
| `app` | 应用管理 | `app.launch`, `app.close`, `app.list` |
| `system` | 系统操作 | `system.info`, `system.lock` |
| `ui` | UI 自动化 | `ui.click`, `ui.type`, `ui.screenshot` |
| `my` | 自定义 | `my.action1`, `my.action2` |

---

## 插件 API

### MCPRequest

插件接收的请求对象：

```python
class MCPRequest:
    id: str                    # 请求唯一 ID
    capability: MCPCapability  # 能力引用
    input: dict                # 输入参数
    context: dict              # 执行上下文
    version: str               # 协议版本（"1.0"）
```

### MCPResponse

插件返回的响应对象：

```python
# 成功响应
MCPResponse.success(request_id, {"result": "ok"})

# 错误响应
MCPResponse.make_error(request_id, "ERROR_CODE", "错误信息")

# 阻止响应（安全策略阻止）
MCPResponse.blocked(request_id, "操作被安全策略阻止")

# 待确认响应（需要用户确认）
MCPResponse.pending_confirm(request_id, "确定要执行吗？", "high")
```

### MCPCapability

能力引用对象：

```python
class MCPCapability:
    namespace: str  # 命名空间（如 "file"）
    action: str     # 动作（如 "read"）

    @property
    def full_name(self) -> str:
        return f"{self.namespace}.{self.action}"  # "file.read"
```

---

## 生命周期钩子

插件可以定义可选的生命周期钩子：

```python
def on_load():
    """插件加载时调用"""
    print("[my.mcp] 插件已加载")
    # 初始化资源、注册事件监听等

def on_unload():
    """插件卸载时调用"""
    print("[my.mcp] 插件已卸载")
    # 清理资源、关闭连接等
```

钩子支持同步和异步函数：

```python
async def on_load():
    """异步加载钩子"""
    await init_database()
```

---

## 内置插件

### file.mcp — 文件系统操作

| 能力 | 参数 | 说明 |
|------|------|------|
| `file.read` | `{path}` | 读取文件内容 |
| `file.write` | `{path, content}` | 写入文件内容 |
| `file.delete` | `{path}` | 删除文件或目录 |
| `file.list` | `{path, pattern?}` | 列出目录内容 |
| `file.copy` | `{from, to}` | 复制文件或目录 |
| `file.move` | `{from, to}` | 移动文件或目录 |
| `file.info` | `{path}` | 获取文件信息 |

### app.mcp — 应用管理

| 能力 | 参数 | 说明 |
|------|------|------|
| `app.launch` | `{app_id, args?}` | 启动应用 |
| `app.close` | `{app_id, pid?}` | 关闭应用 |
| `app.list` | `{}` | 列出运行中的应用 |

### system.mcp — 系统操作

| 能力 | 参数 | 说明 |
|------|------|------|
| `system.info` | `{}` | 获取系统信息 |
| `system.lock` | `{}` | 锁定系统 |
| `system.clipboard.get` | `{}` | 读取剪贴板 |
| `system.clipboard.set` | `{text}` | 写入剪贴板 |

---

## 创建自定义插件

### 示例：Web 抓取插件

```python
"""web.mcp — 网页抓取插件"""

import httpx
from mcp.schema import MCPRequest, MCPResponse


async def execute(request: MCPRequest) -> MCPResponse:
    action = request.capability.action
    input_data = request.input

    if action == "fetch":
        url = input_data.get("url", "")
        if not url:
            return MCPResponse.make_error(request.id, "MISSING_PARAM", "缺少 url 参数")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                return MCPResponse.success(request.id, {
                    "status": resp.status_code,
                    "content": resp.text[:10000],  # 限制长度
                    "headers": dict(resp.headers),
                })
        except Exception as e:
            return MCPResponse.make_error(request.id, "FETCH_ERROR", str(e))

    return MCPResponse.make_error(request.id, "UNSUPPORTED_ACTION", f"不支持: {action}")
```

### plugin.json

```json
{
  "name": "web.mcp",
  "version": "1.0.0",
  "description": "网页抓取插件",
  "capabilities": ["web.fetch"]
}
```

---

## 插件注册与加载

### 自动加载

插件放在 `plugins/` 目录下，Agent 启动时自动扫描并加载：

```
plugins/
├── file.mcp/        # 自动加载
├── app.mcp/         # 自动加载
├── system.mcp/      # 自动加载
└── my.mcp/          # 自动加载
```

### 手动加载

通过 PluginLoader API 手动加载：

```python
from mcp.plugin_loader import PluginLoader
from mcp.router import MCPRouter

loader = PluginLoader(plugins_dir="plugins/")
results = loader.load_all()

# 加载单个插件
result = loader.load_plugin(Path("plugins/my.mcp"))

# 卸载插件
loader.unload_plugin("my.mcp")

# 重载插件
loader.reload_plugin("my.mcp")
```

### 查看已加载插件

```python
# 列出所有插件
plugins = loader.list_plugins()

# 获取插件信息
plugin = loader.router.get_plugin("file.mcp")

# 列出所有能力
capabilities = loader.router.list_capabilities()
```

---

## MCP 协议

### 请求流程

```
1. LLM 生成 tool_call（如 execute_capability）
2. ToolRouter 检查是否有本地插件可处理
3. 如果有 → MCP Router 路由到插件
4. 插件执行并返回 MCPResponse
5. 结果返回给 LLM 生成最终回复
```

### 请求示例

```json
{
  "id": "mcp_abc123",
  "version": "1.0",
  "capability": {
    "namespace": "file",
    "action": "read"
  },
  "input": {
    "path": "/path/to/file.txt"
  },
  "context": {
    "os": "windows",
    "locale": "zh-CN"
  }
}
```

### 响应示例

```json
{
  "id": "mcp_abc123",
  "status": "success",
  "data": {
    "content": "文件内容...",
    "size": 1234,
    "path": "/path/to/file.txt"
  }
}
```

---

## 安全策略

插件执行受 Policy & Safety 层保护：

### 风险评估

| 能力 | 风险等级 | 说明 |
|------|---------|------|
| `file.read` | Low | 自动执行 |
| `file.write` | Medium | 建议确认 |
| `file.delete` | High | 需要确认 |
| `system.shutdown` | High | 需要确认 |

### 权限检查

- 系统关键路径（如 `C:\Windows`）自动阻止
- 高风险操作需要用户确认
- 所有操作记录审计日志

---

## 测试插件

### 单元测试

```python
import pytest
from mcp.schema import MCPRequest, MCPCapability
from mcp.router import MCPRouter
from mcp.plugin_loader import PluginLoader


class TestMyPlugin:

    @pytest.fixture
    def loader(self, tmp_path):
        """创建加载了插件的 loader"""
        plugin_dir = tmp_path / "plugins" / "my.mcp"
        plugin_dir.mkdir(parents=True)

        # 写入 plugin.json
        import json
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": "my.mcp",
                "capabilities": ["my.action"],
            }, f)

        # 复制 plugin.py
        import shutil
        shutil.copy("plugins/my.mcp/plugin.py", plugin_dir / "plugin.py")

        loader = PluginLoader(plugins_dir=tmp_path / "plugins")
        loader.load_all()
        return loader

    def test_action(self, loader):
        """测试 action"""
        import asyncio
        plugin = loader.router.route(MCPCapability("my", "action"))
        req = MCPRequest.create("my", "action", {"data": "test"})
        resp = asyncio.get_event_loop().run_until_complete(plugin.executor(req))
        assert resp.status == "success"
```

### 运行测试

```bash
cd agent
python -m pytest test_my_plugin.py -v
```

---

## 常见问题

### Q: 插件加载失败怎么办？

检查以下几点：
1. `plugin.json` 格式是否正确
2. `plugin.py` 是否有 `execute` 函数
3. 查看 Agent 日志中的错误信息

### Q: 如何调试插件？

1. 在插件中添加 `print()` 或 `logging` 语句
2. 查看 Agent 控制台输出
3. 使用单元测试验证逻辑

### Q: 插件可以访问网络吗？

可以，但需要注意：
- 使用 `httpx` 或 `aiohttp` 进行异步 HTTP 请求
- 设置合理的超时时间
- 处理网络错误

### Q: 插件有性能限制吗？

- 插件执行在 Agent 主进程中
- 避免在插件中执行阻塞操作
- 使用 `async/await` 进行异步操作

### Q: 如何发布插件？

1. 将插件目录打包为 zip
2. 上传到 MCP 市场（开发中）
3. 用户下载后放入 `plugins/` 目录

---

## English Documentation

[Jump to Chinese](#aeralis--mcp-插件开发手册)

### Overview

Auralis's MCP (Model Capability Protocol) plugin system allows developers to extend Agent capabilities through Python modules. Plugins can:

- Register new Capabilities (e.g., `file.search`, `web.scrape`)
- Receive and execute requests through standardized interfaces
- Participate in security policies and audit logging
- Support hot-plugging (load/unload at runtime)

### Quick Start

1. Create plugin directory: `mkdir plugins/my.mcp`
2. Create `plugin.json` with name, version, and capabilities
3. Create `plugin.py` with an `execute` function
4. Restart Agent — plugin loads automatically

### Plugin Structure

```
plugins/my.mcp/
├── plugin.json      # Plugin metadata (required)
├── plugin.py        # Plugin entry point (required)
└── utils.py         # Optional helpers
```

### API Reference

**MCPRequest** — Request object received by plugins:
- `id: str` — Unique request ID
- `capability: MCPCapability` — Capability reference
- `input: dict` — Input parameters
- `context: dict` — Execution context

**MCPResponse** — Response object returned by plugins:
- `MCPResponse.success(id, data)` — Success response
- `MCPResponse.make_error(id, code, message)` — Error response
- `MCPResponse.blocked(id, reason)` — Security blocked
- `MCPResponse.pending_confirm(id, message, risk)` — Needs confirmation

### Built-in Plugins

| Plugin | Capabilities | Description |
|--------|-------------|-------------|
| `file.mcp` | file.read/write/delete/list/copy/move/info | File system operations |
| `app.mcp` | app.launch/close/list | Application management |
| `system.mcp` | system.info/lock/clipboard.get/set | System operations |

### Security

- Risk assessment for all operations (Low/Medium/High)
- System path protection (blocks writes to C:\Windows, etc.)
- User confirmation for high-risk operations
- Full audit logging

### Testing

```bash
cd agent
python -m pytest test_*.py -v
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 项目介绍 |
| [ARCHITECTURE.md](.docs/specs/v1.0.0/ARCHITECTURE.md) | 系统架构 |
| [MCP-PROTOCOL-SPEC.md](.docs/specs/v1.0.0/MCP-PROTOCOL-SPEC.md) | MCP 协议规格 |
| [OS-ADAPTER-SPEC.md](.docs/specs/v1.0.0/OS-ADAPTER-SPEC.md) | OS Adapter 规格 |
| [PRD.md](.docs/specs/v1.0.0/PRD.md) | 产品需求文档 |

---

## 许可证

MIT License
