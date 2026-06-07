"""Function Calling 工具定义 — 供 LLM 调用的工具 Schema"""

# OpenAI Function Calling 格式的工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "settings_query",
            "description": "查询当前应用的所有设置。当用户询问设置、配置、偏好时使用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "settings_change",
            "description": "修改应用设置。当用户要求修改语言、语速、主题等设置时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "changes": {
                        "type": "array",
                        "description": "要修改的设置列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {
                                    "type": "string",
                                    "description": "设置项 key，如 'locale', 'voice.speed', 'appearance.theme'",
                                },
                                "value": {
                                    "description": "新的值",
                                },
                            },
                            "required": ["key", "value"],
                        },
                    },
                },
                "required": ["changes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_capability",
            "description": (
                "执行操作系统级操作，如文件管理、应用管理、系统操作。"
                "⚠️ 危险操作（file.delete, system.shutdown）需要用户明确确认。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "capability_type": {
                        "type": "string",
                        "enum": [
                            "file.list", "file.read", "file.write",
                            "file.delete", "file.move", "file.copy", "file.search",
                            "app.launch", "app.close", "app.list",
                            "system.info", "system.lock", "system.shutdown",
                        ],
                        "description": "操作类型",
                    },
                    "payload": {
                        "type": "object",
                        "description": "操作参数，根据 capability_type 不同而不同",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径（file.read/write/delete 时需要）"},
                            "content": {"type": "string", "description": "文件内容（file.write 时需要）"},
                            "from": {"type": "string", "description": "源路径（file.move/copy 时需要）"},
                            "to": {"type": "string", "description": "目标路径（file.move/copy 时需要）"},
                            "query": {"type": "string", "description": "搜索关键词（file.search 时需要）"},
                            "scope": {"type": "string", "description": "搜索范围路径（file.search 时需要）"},
                            "pattern": {"type": "string", "description": "文件名过滤模式（file.list 时可选，如 *.txt）"},
                            "recursive": {"type": "boolean", "description": "是否递归删除（file.delete 时可选）"},
                            "app_id": {"type": "string", "description": "应用名或可执行文件名（app.launch/close 时需要）"},
                            "args": {"type": "array", "items": {"type": "string"}, "description": "启动参数（app.launch 时可选）"},
                            "pid": {"type": "integer", "description": "进程 ID（app.close 时可选，精确关闭指定进程）"},
                            "delay": {"type": "integer", "description": "延迟关机秒数（system.shutdown 时可选）"},
                        },
                    },
                },
                "required": ["capability_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_settings",
            "description": "打开设置面板。当用户说'打开设置'、'显示设置'时使用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_settings",
            "description": "关闭设置面板。当用户说'关闭设置'时使用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
