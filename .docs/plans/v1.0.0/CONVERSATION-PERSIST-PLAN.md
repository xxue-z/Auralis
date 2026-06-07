# 对话历史持久化实施计划

> Version: 1.0.0 | Created: 2026-06-07 | Status: Draft

---

## 1. 目标

将对话历史从纯内存存储改为 SQLite 持久化，重启后恢复对话上下文。

### 核心能力

| 能力 | 说明 |
|------|------|
| 持久化存储 | 对话消息写入 SQLite，重启不丢失 |
| 会话管理 | 支持多会话，按 session_id 隔离 |
| 历史查询 | 按时间范围、关键词检索历史 |
| 自动清理 | 过期对话自动删除（默认 30 天） |
| 前端同步 | 连接时推送历史消息到前端 |

---

## 2. 架构设计

```
server.py (conversation_history)
  ↓
agent/memory/conversation_store.py (新增)
  ↓
agent/data/conversations.db (SQLite)
```

### 数据库 Schema

```sql
-- 会话表
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title TEXT  -- 首条消息摘要
);

-- 消息表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- user / assistant / tool
    content TEXT,
    tool_calls TEXT,  -- JSON
    tool_call_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
```

---

## 3. 新增/修改文件

### 3.1 新增 `agent/memory/conversation_store.py`

- `ConversationStore` 类
- `save_message(session_id, role, content, ...)`
- `get_history(session_id, limit=20)` → list[dict]
- `list_sessions(limit=50)` → list[session]
- `delete_session(session_id)`
- `cleanup_old(days=30)` → 删除过期数据

### 3.2 修改 `agent/server.py`

- 初始化 `ConversationStore`
- `_handle_with_llm` 从 DB 加载历史（而非仅内存）
- 工具调用结果写入 DB
- 连接时推送历史到前端
- 移除内存 `conversation_history` dict

### 3.3 新增 `agent/test_conversation_persist.py`

---

## 4. 单元测试

| 测试用例 | 说明 |
|----------|------|
| test_save_and_load | 保存消息后能正确加载 |
| test_session_isolation | 不同 session 的消息隔离 |
| test_history_limit | 加载时限制返回数量 |
| test_auto_cleanup | 过期数据自动删除 |
| test_list_sessions | 列出会话列表 |
| test_delete_session | 删除会话及其消息 |
| test_empty_session | 空会话返回空列表 |
| test_concurrent_access | 并发读写安全 |

---

## 5. 实施步骤

1. 创建 `agent/memory/conversation_store.py`
2. 修改 `agent/server.py` 集成 ConversationStore
3. 编写单元测试
4. 本地测试验证
