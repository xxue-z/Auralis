"""file.mcp — 文件系统操作插件"""

import shutil
from pathlib import Path

from mcp.schema import MCPRequest, MCPResponse


async def execute(request: MCPRequest) -> MCPResponse:
    """执行文件操作"""
    action = request.capability.action
    input_data = request.input

    handlers = {
        "read": _handle_read,
        "write": _handle_write,
        "delete": _handle_delete,
        "list": _handle_list,
        "copy": _handle_copy,
        "move": _handle_move,
        "info": _handle_info,
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


async def _handle_read(input_data: dict) -> dict:
    """读取文件内容"""
    path = input_data.get("path", "")
    if not path:
        raise ValueError("缺少 path 参数")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if p.is_dir():
        raise ValueError(f"路径是目录，不是文件: {path}")

    content = p.read_text(encoding="utf-8", errors="replace")
    return {"content": content, "size": len(content), "path": str(p)}


async def _handle_write(input_data: dict) -> dict:
    """写入文件内容"""
    path = input_data.get("path", "")
    content = input_data.get("content", "")
    if not path:
        raise ValueError("缺少 path 参数")

    p = Path(path)
    # 确保父目录存在
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "size": len(content), "written": True}


async def _handle_delete(input_data: dict) -> dict:
    """删除文件或目录"""
    path = input_data.get("path", "")
    if not path:
        raise ValueError("缺少 path 参数")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    if p.is_dir():
        shutil.rmtree(p)
        return {"path": str(p), "type": "directory", "deleted": True}
    else:
        p.unlink()
        return {"path": str(p), "type": "file", "deleted": True}


async def _handle_list(input_data: dict) -> dict:
    """列出目录内容"""
    path = input_data.get("path", ".")
    pattern = input_data.get("pattern")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"目录不存在: {path}")
    if not p.is_dir():
        raise ValueError(f"路径不是目录: {path}")

    entries = []
    for item in sorted(p.iterdir()):
        if pattern and not _match_pattern(pattern, item.name):
            continue
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": stat.st_size,
            })
        except OSError:
            entries.append({"name": item.name, "path": str(item), "is_dir": item.is_dir(), "size": 0})

    return {"path": str(p), "entries": entries, "count": len(entries)}


async def _handle_copy(input_data: dict) -> dict:
    """复制文件或目录"""
    source = input_data.get("from", "")
    destination = input_data.get("to", "")
    if not source or not destination:
        raise ValueError("缺少 from 或 to 参数")

    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"源路径不存在: {source}")

    dst = Path(destination)
    if src.is_dir():
        shutil.copytree(str(src), str(dst))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))

    return {"from": str(src), "to": str(dst), "copied": True}


async def _handle_move(input_data: dict) -> dict:
    """移动文件或目录"""
    source = input_data.get("from", "")
    destination = input_data.get("to", "")
    if not source or not destination:
        raise ValueError("缺少 from 或 to 参数")

    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"源路径不存在: {source}")

    dst = Path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))

    return {"from": str(src), "to": str(dst), "moved": True}


async def _handle_info(input_data: dict) -> dict:
    """获取文件/目录信息"""
    path = input_data.get("path", "")
    if not path:
        raise ValueError("缺少 path 参数")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    stat = p.stat()
    return {
        "path": str(p),
        "name": p.name,
        "is_dir": p.is_dir(),
        "is_file": p.is_file(),
        "size": stat.st_size,
        "extension": p.suffix,
    }


def _match_pattern(pattern: str, name: str) -> bool:
    """简单的 glob 模式匹配"""
    import fnmatch
    return fnmatch.fnmatch(name, pattern)


def on_load():
    """插件加载钩子"""
    print("[file.mcp] 文件系统插件已加载")


def on_unload():
    """插件卸载钩子"""
    print("[file.mcp] 文件系统插件已卸载")
