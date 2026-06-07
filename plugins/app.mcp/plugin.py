"""app.mcp — 应用管理插件"""

import subprocess
import sys
from mcp.schema import MCPRequest, MCPResponse


# 常见应用的可执行文件名映射
APP_ALIASES: dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "msedge": "msedge",
    "notepad": "notepad",
    "记事本": "notepad",
    "explorer": "explorer",
    "文件管理器": "explorer",
    "cmd": "cmd",
    "powershell": "powershell",
    "terminal": "wt",
    "终端": "wt",
    "vscode": "code",
    "visual studio code": "code",
}


async def execute(request: MCPRequest) -> MCPResponse:
    """执行应用操作"""
    action = request.capability.action
    input_data = request.input

    handlers = {
        "launch": _handle_launch,
        "close": _handle_close,
        "list": _handle_list,
    }

    handler = handlers.get(action)
    if not handler:
        return MCPResponse.error(request.id, "UNSUPPORTED_ACTION", f"不支持的操作: {action}")

    try:
        result = await handler(input_data)
        return MCPResponse.success(request.id, result)
    except FileNotFoundError as e:
        return MCPResponse.error(request.id, "NOT_FOUND", str(e))
    except PermissionError as e:
        return MCPResponse.error(request.id, "PERMISSION_DENIED", str(e))
    except Exception as e:
        return MCPResponse.error(request.id, "INTERNAL_ERROR", str(e))


async def _handle_launch(input_data: dict) -> dict:
    """启动应用"""
    app_id = input_data.get("app_id", "")
    if not app_id:
        raise ValueError("缺少 app_id 参数")

    args = input_data.get("args", [])

    # 解析应用名
    executable = APP_ALIASES.get(app_id.lower(), app_id)

    # Windows 平台使用 start 命令
    if sys.platform == "win32":
        cmd = ["cmd", "/c", "start", "", executable] + args
    else:
        cmd = [executable] + args

    try:
        proc = subprocess.Popen(cmd, shell=False)
        return {
            "app_id": app_id,
            "executable": executable,
            "pid": proc.pid,
            "launched": True,
        }
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到应用: {app_id}（可执行文件: {executable}）")


async def _handle_close(input_data: dict) -> dict:
    """关闭应用"""
    app_id = input_data.get("app_id", "")
    pid = input_data.get("pid")

    if not app_id and not pid:
        raise ValueError("需要提供 app_id 或 pid")

    if sys.platform == "win32":
        if pid:
            cmd = ["taskkill", "/PID", str(pid), "/F"]
        else:
            cmd = ["taskkill", "/IM", f"{app_id}.exe", "/F"]
    else:
        if pid:
            cmd = ["kill", "-9", str(pid)]
        else:
            cmd = ["pkill", "-9", app_id]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        success = result.returncode == 0
        return {
            "app_id": app_id,
            "pid": pid,
            "closed": success,
            "message": result.stdout.strip() if success else result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"app_id": app_id, "pid": pid, "closed": False, "message": "关闭超时"}


async def _handle_list(input_data: dict) -> dict:
    """列出运行中的应用"""
    if sys.platform == "win32":
        cmd = ["tasklist", "/FO", "CSV", "/NH"]
    else:
        cmd = ["ps", "aux"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {"processes": [], "count": 0, "error": result.stderr.strip()}

        processes = _parse_process_list(result.stdout)
        return {"processes": processes, "count": len(processes)}
    except subprocess.TimeoutExpired:
        return {"processes": [], "count": 0, "error": "查询超时"}


def _parse_process_list(output: str) -> list[dict]:
    """解析进程列表"""
    processes = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if sys.platform == "win32":
            # CSV 格式: "name","PID","Session","Session#","Mem Usage"
            parts = line.replace('"', '').split(",")
            if len(parts) >= 5:
                processes.append({
                    "name": parts[0],
                    "pid": int(parts[1]) if parts[1].isdigit() else 0,
                    "memory": parts[4],
                })
        else:
            # ps aux 格式
            parts = line.split(None, 10)
            if len(parts) >= 11:
                processes.append({
                    "name": parts[10],
                    "pid": int(parts[1]) if parts[1].isdigit() else 0,
                    "cpu": parts[2],
                    "memory": parts[3],
                })

    return processes


def on_load():
    """插件加载钩子"""
    print("[app.mcp] 应用管理插件已加载")


def on_unload():
    """插件卸载钩子"""
    print("[app.mcp] 应用管理插件已卸载")
