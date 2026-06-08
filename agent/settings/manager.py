"""设置管理器 — 定义设置 Schema，生成 AI 上下文，校验值"""

from typing import Any


# 设置项定义
SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    "locale": {
        "type": "enum", "default": "en-US", "options": ["en-US", "zh-CN"],
        "label": "语言", "description": "应用界面和 AI 回复的语言",
        "ai_editable": True, "confirm_required": True,
    },
    "persona.proactive": {
        "type": "number", "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.1,
        "label": "主动性", "description": "AI 主动发起对话的程度。0=从不主动，1=非常主动",
        "ai_editable": True, "confirm_required": False,
    },
    "persona.humor": {
        "type": "number", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1,
        "label": "幽默度", "description": "AI 回复的幽默程度。0=严肃，1=非常幽默",
        "ai_editable": True, "confirm_required": False,
    },
    "persona.verbosity": {
        "type": "number", "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.1,
        "label": "详细度", "description": "AI 回复的详细程度。0=极简，1=非常详细",
        "ai_editable": True, "confirm_required": False,
    },
    "persona.precision": {
        "type": "number", "default": 0.8, "min": 0.0, "max": 1.0, "step": 0.1,
        "label": "精确度", "description": "AI 操作的谨慎程度。0=大胆，1=非常谨慎",
        "ai_editable": True, "confirm_required": False,
    },
    "model.cloud.provider": {
        "type": "enum", "default": "openai", "options": ["openai", "anthropic", "google"],
        "label": "云端模型", "description": "复杂任务使用的云端 AI 供应商",
        "ai_editable": True, "confirm_required": True,
    },
    "security.confirm_destructive": {
        "type": "boolean", "default": True,
        "label": "确认破坏性操作", "description": "删除文件或修改系统前要求确认",
        "ai_editable": False, "confirm_required": True,
    },
    "security.audit_log": {
        "type": "boolean", "default": True,
        "label": "审计日志", "description": "记录所有操作用于审查和回滚",
        "ai_editable": False, "confirm_required": True,
    },
    "appearance.theme": {
        "type": "enum", "default": "system", "options": ["light", "dark", "system"],
        "label": "主题", "description": "应用颜色主题",
        "ai_editable": True, "confirm_required": False,
    },
    "appearance.chat_color": {
        "type": "string", "default": "#0ea5e9",
        "label": "聊天主题色", "description": "聊天框和按钮的主色调",
        "ai_editable": True, "confirm_required": False,
    },
    "appearance.chat_opacity": {
        "type": "number", "default": 0.9, "min": 0.3, "max": 1.0, "step": 0.05,
        "label": "聊天透明度", "description": "聊天框背景透明度。0.3=透明，1.0=不透明",
        "ai_editable": True, "confirm_required": False,
    },
    "appearance.sprite_size": {
        "type": "number", "default": 96, "min": 64, "max": 200, "step": 8,
        "label": "精灵大小", "description": "桌面精灵的显示尺寸（像素）",
        "ai_editable": True, "confirm_required": False,
    },
    "appearance.sprite_style": {
        "type": "string", "default": "",
        "label": "精灵风格", "description": "精灵的视觉风格（neko/kitsune/fairy/android/blossom）",
        "ai_editable": True, "confirm_required": False,
    },

    # ============ 引导流程 ============
    "onboarding.complete": {
        "type": "boolean", "default": False,
        "label": "引导完成", "description": "是否已完成首次启动引导",
        "ai_editable": False, "confirm_required": False,
    },

    # ============ 语音配置 ============
    "voice.enabled": {
        "type": "boolean", "default": False,
        "label": "启用语音", "description": "启用语音回答功能",
        "ai_editable": True, "confirm_required": False,
    },
    "voice.preset_id": {
        "type": "enum", "default": "sweet_female",
        "options": ["sweet_female", "cute_female", "cool_female", "gentle_male", "energetic_male", "neutral", "custom"],
        "label": "音线", "description": "精灵的语音音色",
        "ai_editable": True, "confirm_required": False,
    },
    "voice.provider": {
        "type": "enum", "default": "edge",
        "options": ["edge", "openai", "xiaomi", "kokoro"],
        "label": "TTS 引擎", "description": "语音合成引擎（edge 免费，xiaomi 小米 MiMo，kokoro 本地测试版）",
        "ai_editable": True, "confirm_required": True,
    },
    "voice.speed": {
        "type": "number", "default": 1.0, "min": 0.5, "max": 2.0, "step": 0.1,
        "label": "语速", "description": "语音输出的语速",
        "ai_editable": True, "confirm_required": False,
    },
    "voice.pitch": {
        "type": "number", "default": 1.0, "min": 0.5, "max": 2.0, "step": 0.1,
        "label": "音调", "description": "语音输出的音调",
        "ai_editable": True, "confirm_required": False,
    },
    "voice.custom_clone_id": {
        "type": "string", "default": "",
        "label": "克隆音色 ID", "description": "用户上传音频克隆的音色标识",
        "ai_editable": False, "confirm_required": False,
    },

    # ============ 云端模型配置 ============
    "model.cloud.enabled": {
        "type": "boolean", "default": True,
        "label": "启用云端模型", "description": "是否使用云端 AI 模型",
        "ai_editable": True, "confirm_required": True,
    },
    "model.cloud.vendor": {
        "type": "string", "default": "OpenAI",
        "label": "云端厂商", "description": "选中的云端 AI 厂商",
        "ai_editable": True, "confirm_required": True,
    },
    "model.cloud.base_url": {
        "type": "string", "default": "https://api.openai.com/v1",
        "label": "API 地址", "description": "云端 API 的 Base URL",
        "ai_editable": True, "confirm_required": True,
    },
    "model.cloud.api_protocol": {
        "type": "enum", "default": "openai", "options": ["openai", "anthropic"],
        "label": "API 协议", "description": "API 调用协议（openai 或 anthropic）",
        "ai_editable": True, "confirm_required": True,
    },
    "model.cloud.api_key": {
        "type": "string", "default": "",
        "label": "API Key", "description": "云端 API 密钥（加密存储）",
        "ai_editable": False, "confirm_required": True,
    },
    "model.cloud.model_id": {
        "type": "string", "default": "gpt-4o",
        "label": "云端模型", "description": "选中的云端模型 ID",
        "ai_editable": True, "confirm_required": True,
    },
    "model.cloud.custom_vendors": {
        "type": "string", "default": "[]",
        "label": "自定义厂商", "description": "用户自定义的云端厂商列表（JSON）",
        "ai_editable": False, "confirm_required": False,
    },

    # ============ 本地模型配置（Ollama）============
    "model.local.enabled": {
        "type": "boolean", "default": False,
        "label": "启用本地模型", "description": "启用 Ollama 本地模型，需要先安装 Ollama",
        "ai_editable": True, "confirm_required": True,
    },
    "model.local.base_url": {
        "type": "string", "default": "http://localhost:11434/v1",
        "label": "Ollama 地址", "description": "Ollama API 地址",
        "ai_editable": True, "confirm_required": False,
    },
    "model.local.model_id": {
        "type": "string", "default": "qwen2.5:1.5b",
        "label": "本地模型", "description": "选中的本地模型 ID",
        "ai_editable": True, "confirm_required": False,
    },

    # ============ 通用模型配置 ============
    "model.auto_switch": {
        "type": "boolean", "default": True,
        "label": "自动切换", "description": "云端不可用时自动切换到本地模型",
        "ai_editable": True, "confirm_required": False,
    },

    # ============ 通知设置 ============
    "notifications.enabled": {
        "type": "boolean", "default": True,
        "label": "启用通知", "description": "显示 AI 建议和提醒的通知",
        "ai_editable": True, "confirm_required": False,
    },
    "notifications.sound": {
        "type": "boolean", "default": True,
        "label": "通知声音", "description": "显示通知时播放提示音",
        "ai_editable": True, "confirm_required": False,
    },

    # ============ 高级设置 ============
    "advanced.debug_mode": {
        "type": "boolean", "default": False,
        "label": "调试模式", "description": "启用调试日志和开发者工具",
        "ai_editable": True, "confirm_required": False,
    },
    "advanced.auto_update": {
        "type": "boolean", "default": True,
        "label": "自动更新", "description": "自动检查并安装更新",
        "ai_editable": True, "confirm_required": False,
    },
    "advanced.memory_retention_days": {
        "type": "number", "default": 90, "min": 7, "max": 365, "step": 7,
        "label": "记忆保留天数", "description": "对话和事件记忆的保留天数",
        "ai_editable": True, "confirm_required": False,
    },
}


def get_settings_context() -> str:
    """生成设置上下文，注入到 LLM prompt 或规则引擎中"""
    lines = ["当前应用设置："]
    for key, defn in SETTINGS_SCHEMA.items():
        editable = "可修改" if defn["ai_editable"] else "只读"
        lines.append(f"  {key} = {defn['default']}  # {defn['label']} - {defn['description']} [{editable}]")
    return "\n".join(lines)


def get_all_settings() -> dict[str, Any]:
    """返回所有设置的默认值"""
    return {key: defn["default"] for key, defn in SETTINGS_SCHEMA.items()}


def get_setting_definition(key: str) -> dict | None:
    return SETTINGS_SCHEMA.get(key)


def is_ai_editable(key: str) -> bool:
    defn = SETTINGS_SCHEMA.get(key)
    return defn.get("ai_editable", False) if defn else False


def requires_confirmation(key: str) -> bool:
    defn = SETTINGS_SCHEMA.get(key)
    return defn.get("confirm_required", True) if defn else True


def validate_setting_value(key: str, value: Any) -> tuple[bool, str]:
    """校验设置值是否合法，返回 (valid, error_message)"""
    defn = SETTINGS_SCHEMA.get(key)
    if not defn:
        return False, f"未知设置项: {key}"

    t = defn["type"]

    if t == "enum":
        if value not in defn["options"]:
            return False, f"'{key}' 的值必须是 {defn['options']} 之一，收到: {value}"

    elif t == "number":
        if not isinstance(value, (int, float)):
            return False, f"'{key}' 必须是数字"
        if "min" in defn and value < defn["min"]:
            return False, f"'{key}' 不能小于 {defn['min']}"
        if "max" in defn and value > defn["max"]:
            return False, f"'{key}' 不能大于 {defn['max']}"

    elif t == "boolean":
        if not isinstance(value, bool):
            return False, f"'{key}' 必须是 true 或 false"

    elif t == "string":
        if not isinstance(value, str):
            return False, f"'{key}' 必须是字符串"

    return True, ""
