"""AI 设置修改处理 — 处理 settings_query 和 settings_change"""

from typing import Any
from settings.manager import (
    SETTINGS_SCHEMA, is_ai_editable, requires_confirmation,
    validate_setting_value, get_all_settings, get_setting_definition,
)


def handle_settings_query() -> dict:
    """处理设置查询请求，返回所有设置的当前值"""
    settings = get_all_settings()
    # 格式化为可读列表
    items = []
    for key, value in settings.items():
        defn = get_setting_definition(key)
        if defn:
            items.append({
                "key": key,
                "value": value,
                "label": defn["label"],
                "description": defn["description"],
                "editable": defn["ai_editable"],
            })
    return {
        "type": "settings_query_result",
        "settings": items,
    }


def handle_settings_change(changes: list[dict[str, Any]]) -> dict:
    """处理设置修改请求
    changes: [{"key": "locale", "value": "zh-CN"}, ...]
    返回: {"type": "settings_change_result", "results": [...]}
    """
    results = []

    for change in changes:
        key = change.get("key", "")
        value = change.get("value")

        # 检查设置是否存在
        defn = get_setting_definition(key)
        if not defn:
            results.append({"key": key, "success": False, "error": f"未知设置项: {key}"})
            continue

        # 检查 AI 是否有权限修改
        if not is_ai_editable(key):
            results.append({
                "key": key, "success": False,
                "error": f"'{defn['label']}' 出于安全考虑不允许 AI 修改，请在设置面板中手动更改",
            })
            continue

        # 校验值
        valid, error = validate_setting_value(key, value)
        if not valid:
            results.append({"key": key, "success": False, "error": error})
            continue

        # 检查是否需要确认
        if requires_confirmation(key):
            results.append({
                "key": key, "success": False, "needs_confirm": True,
                "message": f"要把 {defn['label']} 改成 {value} 吗？",
            })
            continue

        # 通过校验，标记为待应用（前端负责实际应用）
        results.append({
            "key": key, "success": True, "value": value,
            "label": defn["label"],
        })

    return {
        "type": "settings_change_result",
        "results": results,
    }


def format_settings_reply(query_result: dict) -> str:
    """将设置查询结果格式化为自然语言回复"""
    settings = query_result.get("settings", [])
    if not settings:
        return "暂无设置信息。"

    lines = ["你的当前设置：\n"]
    for s in settings:
        editable_mark = "" if s["editable"] else " 🔒"
        lines.append(f"• {s['label']}: {s['value']}{editable_mark}")
    lines.append("\n你可以告诉我想修改哪项设置。")
    return "\n".join(lines)


def format_change_reply(change_result: dict) -> str:
    """将设置修改结果格式化为自然语言回复"""
    results = change_result.get("results", [])
    if not results:
        return "没有需要修改的设置。"

    lines = []
    for r in results:
        if r.get("success"):
            lines.append(f"✅ 已将 {r['label']} 改成 {r['value']}")
        elif r.get("needs_confirm"):
            lines.append(f"⚠️ {r['message']}")
        else:
            lines.append(f"❌ {r['error']}")

    return "\n".join(lines)
