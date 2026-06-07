"""system.mcp — 系统操作插件"""

import platform
import subprocess
import sys
from mcp.schema import MCPRequest, MCPResponse


async def execute(request: MCPRequest) -> MCPResponse:
    """执行系统操作"""
    action = request.capability.action
    input_data = request.input

    handlers = {
        "info": _handle_info,
        "lock": _handle_lock,
        "clipboard.get": _handle_clipboard_get,
        "clipboard.set": _handle_clipboard_set,
    }

    handler = handlers.get(action)
    if not handler:
        return MCPResponse.error(request.id, "UNSUPPORTED_ACTION", f"不支持的操作: {action}")

    try:
        result = await handler(input_data)
        return MCPResponse.success(request.id, result)
    except Exception as e:
        return MCPResponse.error(request.id, "INTERNAL_ERROR", str(e))


async def _handle_info(input_data: dict) -> dict:
    """获取系统信息"""
    import os

    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
    }

    # 尝试获取 CPU 和内存信息（psutil 可选）
    try:
        import psutil
        info["cpu_count"] = psutil.cpu_count()
        info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        info["memory_total"] = mem.total
        info["memory_available"] = mem.available
        info["memory_percent"] = mem.percent
        disk = psutil.disk_usage("/")
        info["disk_total"] = disk.total
        info["disk_used"] = disk.used
        info["disk_percent"] = disk.percent
    except ImportError:
        # psutil 不可用，使用基础信息
        info["cpu_count"] = os.cpu_count()

    return info


async def _handle_lock(input_data: dict) -> dict:
    """锁定系统"""
    if sys.platform == "win32":
        # Windows: 使用 rundll32 锁屏
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
    elif sys.platform == "darwin":
        # macOS
        subprocess.Popen([
            "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
            "-suspend",
        ])
    else:
        # Linux
        subprocess.Popen(["xdg-screensaver", "lock"])

    return {"locked": True, "platform": sys.platform}


async def _handle_clipboard_get(input_data: dict) -> dict:
    """读取剪贴板内容"""
    if sys.platform == "win32":
        # Windows: 使用 powershell 读取剪贴板
        result = subprocess.run(
            ["powershell", "-command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        text = result.stdout.strip()
    elif sys.platform == "darwin":
        # macOS
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True, text=True, timeout=5,
        )
        text = result.stdout
    else:
        # Linux
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True, timeout=5,
        )
        text = result.stdout

    return {"text": text, "length": len(text)}


async def _handle_clipboard_set(input_data: dict) -> dict:
    """写入剪贴板内容"""
    text = input_data.get("text", "")
    if not text:
        return {"success": False, "error": "text 参数为空"}

    if sys.platform == "win32":
        # Windows: 使用 powershell 写入剪贴板
        # 使用 stdin 传递文本，避免命令行转义问题
        proc = subprocess.Popen(
            ["powershell", "-command", "Set-Clipboard -Value $input"],
            stdin=subprocess.PIPE, text=True,
        )
        proc.communicate(input=text)
    elif sys.platform == "darwin":
        # macOS
        proc = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE, text=True,
        )
        proc.communicate(input=text)
    else:
        # Linux
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE, text=True,
        )
        proc.communicate(input=text)

    return {"success": True, "length": len(text)}


def on_load():
    """插件加载钩子"""
    print("[system.mcp] 系统操作插件已加载")


def on_unload():
    """插件卸载钩子"""
    print("[system.mcp] 系统操作插件已卸载")
