# LLM 接入实施计划

> Version: 1.0.0 | Created: 2026-06-07 | Status: Draft

---

## 1. 目标

将已实现的 `model/cloud.py` 和 `model/router.py` 接入 `server.py`，使 Agent 能通过 LLM 理解自然语言，替代纯规则匹配。

### 核心能力

| 能力 | 说明 |
|------|------|
| 自然语言对话 | 用户说任意内容，LLM 生成回复 |
| Function Calling | LLM 调用 settings_query/settings_change/capability 工具 |
| 流式输出 | LLM 回复流式推送到前端 |
| 规则降级 | LLM 不可用时回退到规则匹配 |
| 对话历史 | 维护会话上下文（内存，暂不持久化） |

---

## 2. 架构变更

```
用户消息
  ↓
IntentParser.parse() → 如果是明确意图（settings_open 等），直接处理
  ↓ unknown
ModelRouter.chat() → LLM 理解 + Function Calling
  ↓
解析 LLM 返回 → 执行工具调用 → 组装最终回复
  ↓
send_text_response() → 流式推送
```

---

## 3. 新增/修改文件

### 3.1 新增 `agent/prompts/system.py` — 系统提示词

```python
SYSTEM_PROMPT = """你是 Auralis，一个桌面精灵操作系统智能体。
你常驻用户桌面，用自然语言帮助用户操作电脑。

## 你的能力
- 文件操作：扫描、读取、删除文件
- 应用管理：启动、关闭、列出应用
- 系统操作：查看系统信息、锁屏
- 设置管理：查询和修改应用设置

## 设置修改规则
- 修改设置前先确认用户意图
- 安全相关设置（security.*）不允许 AI 关闭
- 修改后告知用户结果

## 回复风格
- 简洁友好，像精灵一样活泼
- 执行操作时先告知用户你在做什么
- 出错时给出清晰的错误信息和建议
"""
```

### 3.2 新增 `agent/tools/functions.py` — Function Calling 定义

定义 LLM 可调用的工具：
- `settings_query` — 查询设置
- `settings_change` — 修改设置
- `execute_capability` — 执行 OS 操作（文件/应用/系统）
- `open_settings` — 打开设置面板
- `close_settings` — 关闭设置面板

### 3.3 修改 `agent/model/cloud.py` — 添加 tools 参数

在 `chat()` 和 `_call_openai()` 中支持 `tools` 参数，传递给 API。

### 3.4 修改 `agent/server.py` — 核心集成

- 导入 `ModelRouter`、系统提示词、工具定义
- `handle_user_message` 中：规则匹配 unknown 时调用 LLM
- 处理 LLM 返回的 tool_calls → 执行对应操作
- 维护 `conversation_history` 字典（per session）
- 流式推送 LLM 回复

### 3.5 新增 `agent/test_llm_integration.py` — 单元测试

---

## 4. 单元测试

| 测试用例 | 说明 |
|----------|------|
| test_system_prompt_build | 系统提示词包含必要信息 |
| test_tools_definition_valid | 工具定义符合 OpenAI schema |
| test_rule_fallback | 规则匹配的意图不走 LLM |
| test_llm_chat_call | LLM 调用参数正确 |
| test_tool_call_parse | 解析 LLM 返回的 tool_calls |
| test_settings_query_via_llm | LLM 调用 settings_query 工具 |
| test_settings_change_via_llm | LLM 调用 settings_change 工具 |
| test_capability_via_llm | LLM 调用 execute_capability 工具 |
| test_conversation_history | 对话历史正确维护 |
| test_llm_error_fallback | LLM 失败时回退到规则匹配 |

---

## 5. 实施步骤

1. 创建 `agent/prompts/system.py`
2. 创建 `agent/tools/functions.py`
3. 修改 `agent/model/cloud.py` 添加 tools 支持
4. 修改 `agent/server.py` 集成 LLM
5. 编写单元测试
6. 本地测试验证
