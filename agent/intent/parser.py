"""意图解析器 — 基于规则的意图识别（Phase 1）"""

import os
import uuid
from typing import Optional


class IntentParser:
    """将用户自然语言解析为结构化意图和 Capability 请求"""

    # 关键词 → 意图映射
    KEYWORD_MAP = {
        # 文件操作
        ("扫描", "列出", "查看", "文件列表", "有什么文件"): "file_list",
        ("清理", "删除", "垃圾", "清除", "去掉"): "file_delete",
        ("读取", "打开文件", "读文件", "查看内容"): "file_read",
        # 应用操作
        ("打开", "启动", "运行", "开启"): "app_launch",
        ("关闭", "退出", "结束", "杀掉"): "app_close",
        ("进程", "运行中", "正在运行"): "app_list",
        # 系统操作
        ("系统信息", "电脑信息", "配置", "硬件"): "system_info",
        ("锁屏", "锁定"): "system_lock",
        # 设置操作
        ("设置", "配置", "偏好", "我的设置", "当前设置"): "settings_query",
    }

    # 设置修改关键词模式：需要同时匹配"修改动作"和"设置项"
    SETTINGS_CHANGE_ACTIONS = (
        "改成", "调成", "设置为", "切换", "换成", "改为", "调到",
        "调高", "调低", "高一点", "低一点", "大一点", "小一点",
        "一点", "一些", "更", "开启", "关闭", "启用", "禁用",
    )
    SETTINGS_KEYS = {
        "语言": "locale",
        "英文": ("locale", "en-US"),
        "中文": ("locale", "zh-CN"),
        "幽默": "persona.humor",
        "详细": "persona.verbosity",
        "简洁": "persona.verbosity",
        "主动": "persona.proactive",
        "精确": "persona.precision",
        "语速": "voice.speed",
        "主题": "appearance.theme",
        "深色": ("appearance.theme", "dark"),
        "浅色": ("appearance.theme", "light"),
        "暗色": ("appearance.theme", "dark"),
        "亮色": ("appearance.theme", "light"),
    }

    # 常见应用名 → 可执行文件映射
    APP_MAP = {
        "记事本": "notepad",
        "计算器": "calc",
        "画图": "mspaint",
        "浏览器": "msedge",
        "chrome": "chrome",
        "谷歌": "chrome",
        "文件管理器": "explorer",
        "资源管理器": "explorer",
        "终端": "wt",
        "命令行": "cmd",
        "powershell": "powershell",
        "vscode": "code",
        "vs code": "code",
    }

    # 复合短语优先匹配（避免"打开设置"被拆成"打开"→app_launch）
    COMPOUND_PHRASES = {
        ("打开设置", "打开配置", "显示设置", "显示配置", "设置面板", "打开偏好"): "settings_open",
        ("打开文件", "读取文件"): "file_read",
        ("关闭设置", "关闭配置"): "settings_close",
    }

    def parse(self, user_input: str) -> dict:
        """解析用户输入，返回意图和生成的 Capability 列表"""
        text = user_input.strip().lower()

        # 1. 优先匹配复合短语
        for phrases, intent in self.COMPOUND_PHRASES.items():
            for phrase in phrases:
                if phrase in text:
                    return {
                        "intent": intent,
                        "capabilities": [],
                        "reply": None,
                    }

        # 2. 检查是否是设置修改
        settings_change = self._match_settings_change(text)
        if settings_change:
            return settings_change

        # 3. 匹配其他意图
        intent = self._match_intent(text)
        if not intent:
            return {"intent": "unknown", "capabilities": [], "reply": None}

        # 生成 Capability
        capabilities = self._generate_capabilities(intent, text)

        # 生成确认回复
        reply = self._generate_reply(intent, text, capabilities)

        return {
            "intent": intent,
            "capabilities": capabilities,
            "reply": reply,
        }

    def _match_intent(self, text: str) -> Optional[str]:
        """关键词匹配意图"""
        for keywords, intent in self.KEYWORD_MAP.items():
            for kw in keywords:
                if kw in text:
                    return intent
        return None

    def _match_settings_change(self, text: str) -> Optional[dict]:
        """匹配设置修改意图，返回 None 如果不是设置修改"""
        # 检查是否包含修改动作
        has_action = any(action in text for action in self.SETTINGS_CHANGE_ACTIONS)
        if not has_action:
            return None

        # 尝试匹配设置项
        changes = []
        for keyword, target in self.SETTINGS_KEYS.items():
            if keyword not in text:
                continue

            if isinstance(target, tuple):
                # 直接指定了 key 和 value，如 "中文" → ("locale", "zh-CN")
                key, value = target
                changes.append({"key": key, "value": value})
            else:
                # 只匹配了 key，需要从文本中提取 value
                key = target
                value = self._extract_setting_value(text, key)
                if value is not None:
                    changes.append({"key": key, "value": value})

        if not changes:
            return None

        return {
            "intent": "settings_change",
            "capabilities": [],
            "settings_changes": changes,
            "reply": None,  # 由 ai_handler 格式化回复
        }

    def _extract_setting_value(self, text: str, key: str) -> Optional:
        """从文本中提取设置值"""
        import re

        # 匹配明确的数字
        num_match = re.search(r'(\d+\.?\d*)', text)
        if num_match and (key.startswith("persona.") or key == "voice.speed"):
            return float(num_match.group(1))

        # "调高" / "调低" / "一点" / "一些" 逻辑（数值类设置）
        if any(w in text for w in ("调高", "高一点", "大一点", "一点", "一些", "更")):
            if key.startswith("persona.") or key == "voice.speed":
                return "increase"
        if any(w in text for w in ("调低", "低一点", "小一点")):
            if key.startswith("persona.") or key == "voice.speed":
                return "decrease"

        # 布尔值
        if any(w in text for w in ("开启", "启用", "打开")):
            return True
        if any(w in text for w in ("关闭", "禁用", "关掉")):
            return False

        return None

    def _generate_capabilities(self, intent: str, text: str) -> list[dict]:
        """根据意图生成 Capability 请求列表"""
        cap_id = str(uuid.uuid4())[:8]

        if intent == "file_list":
            # 确定扫描路径
            path = self._extract_path(text)
            return [{
                "id": cap_id,
                "capability": {"type": "file.list", "payload": {"path": path, "pattern": None}},
            }]

        elif intent == "file_delete":
            path = self._extract_path(text)
            return [{
                "id": cap_id,
                "capability": {"type": "file.list", "payload": {"path": path, "pattern": None}},
            }]

        elif intent == "file_read":
            path = self._extract_path(text)
            return [{
                "id": cap_id,
                "capability": {"type": "file.read", "payload": {"path": path}},
            }]

        elif intent == "app_launch":
            app_id = self._extract_app(text)
            return [{
                "id": cap_id,
                "capability": {"type": "app.launch", "payload": {"app_id": app_id, "args": None}},
            }]

        elif intent == "app_close":
            app_id = self._extract_app(text)
            return [{
                "id": cap_id,
                "capability": {"type": "app.close", "payload": {"app_id": app_id, "pid": None}},
            }]

        elif intent == "app_list":
            return [{
                "id": cap_id,
                "capability": {"type": "app.list", "payload": {}},
            }]

        elif intent == "system_info":
            return [{
                "id": cap_id,
                "capability": {"type": "system.info", "payload": {}},
            }]

        elif intent == "system_lock":
            return [{
                "id": cap_id,
                "capability": {"type": "system.lock", "payload": {}},
            }]

        return []

    def _extract_path(self, text: str) -> str:
        """从文本中提取文件路径，或根据关键词推断"""
        # 如果文本中包含绝对路径
        for word in text.split():
            if os.path.isabs(word):
                return word

        # 根据关键词推断目录
        if "桌面" in text or "desktop" in text:
            return os.path.expanduser("~/Desktop")
        if "下载" in text or "download" in text:
            return os.path.expanduser("~/Downloads")
        if "文档" in text or "document" in text:
            return os.path.expanduser("~/Documents")
        if "临时" in text or "temp" in text:
            return os.environ.get("TEMP", os.path.expanduser("~/AppData/Local/Temp"))

        # 默认桌面
        return os.path.expanduser("~/Desktop")

    def _extract_app(self, text: str) -> str:
        """从文本中提取应用名"""
        for name, exe in self.APP_MAP.items():
            if name in text:
                return exe
        # 尝试直接使用文本中的单词
        for word in text.split():
            if len(word) > 2 and word not in ("打开", "启动", "关闭", "退出", "运行", "帮我", "一下"):
                return word
        return "notepad"  # 默认

    def _generate_reply(self, intent: str, text: str, capabilities: list[dict]) -> str:
        """生成 Agent 的确认回复"""
        if intent == "file_list":
            path = capabilities[0]["capability"]["payload"]["path"]
            return f"好的，我来扫描 {path} 目录下的文件。"
        elif intent == "file_delete":
            path = capabilities[0]["capability"]["payload"]["path"]
            return f"好的，我先扫描 {path}，看看有哪些可以清理的文件。"
        elif intent == "file_read":
            path = capabilities[0]["capability"]["payload"]["path"]
            return f"好的，我来读取 {path} 的内容。"
        elif intent == "app_launch":
            app = capabilities[0]["capability"]["payload"]["app_id"]
            return f"正在为你打开 {app}..."
        elif intent == "app_close":
            app = capabilities[0]["capability"]["payload"]["app_id"]
            return f"正在关闭 {app}..."
        elif intent == "app_list":
            return "正在获取运行中的应用列表..."
        elif intent == "system_info":
            return "正在获取系统信息..."
        elif intent == "system_lock":
            return "正在锁定系统..."
        elif intent == "settings_query":
            return None  # 由 ai_handler 格式化
        elif intent == "settings_change":
            return None  # 由 ai_handler 格式化
        return ""
