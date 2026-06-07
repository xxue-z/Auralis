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
            "description": "执行操作系统级操作，如文件管理、应用管理、系统操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "capability_type": {
                        "type": "string",
                        "enum": [
                            "file.list", "file.read",
                            "app.launch", "app.close", "app.list",
                            "system.info", "system.lock",
                        ],
                        "description": "操作类型",
                    },
                    "payload": {
                        "type": "object",
                        "description": "操作参数。file.list/file.read 需要 path；app.launch/app.close 需要 app_id",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径（file.list/file.read 时需要）"},
                            "app_id": {"type": "string", "description": "应用名或可执行文件名（app.launch/app.close 时需要）"},
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


# 工具名称 → 对应 capability_type 的映射
TOOL_CAPABILITY_MAP = {
    "file.list": "file.list",
    "file.read": "file.read",
    "app.launch": "app.launch",
    "app.close": "app.close",
    "app.list": "app.list",
    "system.info": "system.info",
    "system.lock": "system.lock",
}
