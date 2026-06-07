"""Auralis Agent WebSocket 服务端"""

import asyncio
import base64
import json
import logging
import uuid
import websockets
from websockets.server import WebSocketServerProtocol

from config import config
from intent.parser import IntentParser
from settings.ai_handler import (
    handle_settings_query, handle_settings_change,
    format_settings_reply, format_change_reply,
)
from tts.router import TTSRouter
from tts.clone import VoiceCloner
from tts.generator import VoiceGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("auralis.agent")

connected_clients: set[WebSocketServerProtocol] = set()
intent_parser = IntentParser()
tts_router = TTSRouter()
voice_cloner = VoiceCloner()
voice_generator = VoiceGenerator()

# 等待前端返回 capability 执行结果的回调
pending_results: dict[str, asyncio.Future] = {}

# 用户设置缓存（前端同步过来的）
user_settings: dict = {}


async def handle_message(ws: WebSocketServerProtocol, raw: str):
    try:
        data = json.loads(raw)
        msg_type = data.get("type")
        logger.info(f"收到消息: type={msg_type}")

        if msg_type == "user_message":
            await handle_user_message(ws, data)
        elif msg_type == "capability_result":
            await handle_capability_result(ws, data)
        elif msg_type == "settings_query_result":
            await handle_settings_result(ws, data)
        elif msg_type == "settings_change_result":
            await handle_settings_result(ws, data)
        elif msg_type == "settings_update":
            # 前端同步设置到 Agent
            user_settings.update(data.get("settings", {}))
            logger.info(f"设置同步: {list(data.get('settings', {}).keys())}")
        elif msg_type == "voice_clone":
            await handle_voice_clone(ws, data)
        elif msg_type == "voice_generate":
            await handle_voice_generate(ws, data)
        elif msg_type == "confirm_response":
            await handle_confirm_response(ws, data)
        else:
            logger.warning(f"未知消息类型: {msg_type}")
    except json.JSONDecodeError:
        logger.error(f"JSON 解析失败: {raw[:100]}")
    except Exception as e:
        logger.error(f"处理消息异常: {e}", exc_info=True)


async def handle_user_message(ws: WebSocketServerProtocol, data: dict):
    content = data.get("content", "")
    message_id = data.get("id", "")
    logger.info(f"用户消息: {content}")

    # 意图识别
    result = intent_parser.parse(content)
    logger.info(f"意图识别: {result['intent']}")

    if result["intent"] == "unknown":
        await send_text_response(ws, message_id,
            f"抱歉，我不太理解「{content}」的意思。\n\n"
            "你可以试试：\n"
            "• 扫描桌面文件\n"
            "• 打开记事本\n"
            "• 查看系统信息\n"
            "• 列出运行中的应用\n"
            "• 打开设置\n"
            "• 把语言改成中文\n"
            "• 我现在的设置是什么"
        )
        return

    # 打开设置面板
    if result["intent"] == "settings_open":
        await ws.send(json.dumps({
            "type": "agent_command",
            "command": "open-settings",
        }))
        await send_text_response(ws, message_id, "好的，已为你打开设置面板。")
        return

    # 关闭设置面板
    if result["intent"] == "settings_close":
        await ws.send(json.dumps({
            "type": "agent_command",
            "command": "close-settings",
        }))
        await send_text_response(ws, message_id, "设置面板已关闭。")
        return

    # 设置查询
    if result["intent"] == "settings_query":
        request_id = str(uuid.uuid4())[:8]
        future = asyncio.get_event_loop().create_future()
        pending_results[request_id] = future

        await ws.send(json.dumps({
            "type": "settings_query",
            "request_id": request_id,
        }))

        try:
            query_result = await asyncio.wait_for(future, timeout=10.0)
            reply = format_settings_reply(query_result)
            await send_text_response(ws, message_id, reply)
        except asyncio.TimeoutError:
            await send_text_response(ws, message_id, "获取设置超时，请重试。")
        finally:
            pending_results.pop(request_id, None)
        return

    # 设置修改
    if result["intent"] == "settings_change":
        changes = result.get("settings_changes", [])
        if not changes:
            await send_text_response(ws, message_id, "请告诉我你想修改什么设置。")
            return

        # 先校验
        change_result = handle_settings_change(changes)

        # 检查是否全部需要确认
        needs_confirm = [r for r in change_result["results"] if r.get("needs_confirm")]
        ready_changes = [r for r in change_result["results"] if r.get("success")]

        if needs_confirm:
            # 告诉用户需要确认
            confirm_msg = "\n".join(r["message"] for r in needs_confirm)
            await send_text_response(ws, message_id, f"需要你的确认：\n{confirm_msg}")
            # TODO: 等待用户确认后重新执行
            return

        if ready_changes:
            # 发给前端应用
            request_id = str(uuid.uuid4())[:8]
            future = asyncio.get_event_loop().create_future()
            pending_results[request_id] = future

            await ws.send(json.dumps({
                "type": "settings_change",
                "request_id": request_id,
                "changes": [{"key": r["key"], "value": r["value"]} for r in ready_changes],
            }))

            try:
                apply_result = await asyncio.wait_for(future, timeout=10.0)
                reply = format_change_reply(apply_result)
                await send_text_response(ws, message_id, reply)
            except asyncio.TimeoutError:
                await send_text_response(ws, message_id, "设置修改超时，请重试。")
            finally:
                pending_results.pop(request_id, None)
            return

        # 有错误
        reply = format_change_reply(change_result)
        await send_text_response(ws, message_id, reply)
        return

    # 先发送 Agent 的确认回复
    if result["reply"]:
        await send_text_response(ws, message_id, result["reply"])

    # 发送 capability 请求给前端执行
    if result["capabilities"]:
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"发送 capability 请求: {request_id}, {len(result['capabilities'])} 个操作")

        future = asyncio.get_event_loop().create_future()
        pending_results[request_id] = future

        await ws.send(json.dumps({
            "type": "capability_request",
            "request_id": request_id,
            "capabilities": result["capabilities"],
        }))

        try:
            cap_results = await asyncio.wait_for(future, timeout=30.0)
            reply = format_capability_results(result["intent"], cap_results)
            await send_text_response(ws, message_id, reply)
        except asyncio.TimeoutError:
            await send_text_response(ws, message_id, "操作执行超时，请重试。")
        finally:
            pending_results.pop(request_id, None)


async def handle_capability_result(ws: WebSocketServerProtocol, data: dict):
    """处理前端返回的 capability 执行结果"""
    request_id = data.get("request_id")
    results = data.get("results", [])
    logger.info(f"收到 capability 结果: request_id={request_id}, {len(results)} 个结果")

    future = pending_results.get(request_id)
    if future and not future.done():
        future.set_result(results)


async def handle_settings_result(ws: WebSocketServerProtocol, data: dict):
    """处理前端返回的设置查询/修改结果"""
    request_id = data.get("request_id")
    logger.info(f"收到设置结果: request_id={request_id}")

    future = pending_results.get(request_id)
    if future and not future.done():
        future.set_result(data)


async def handle_voice_clone(ws: WebSocketServerProtocol, data: dict):
    """处理声音克隆请求"""
    try:
        audio_b64 = data.get("audio")
        filename = data.get("filename", "voice.wav")

        if not audio_b64:
            await ws.send(json.dumps({
                "type": "voice_clone_result",
                "success": False,
                "error": "未提供音频数据",
            }))
            return

        audio_data = base64.b64decode(audio_b64)
        result = await voice_cloner.clone_from_audio(audio_data, filename, user_settings)

        # 注册到 TTS Router
        tts_router.register_custom_voice(result["voice_id"], result["config"])

        await ws.send(json.dumps({
            "type": "voice_clone_result",
            "success": True,
            "voice_id": result["voice_id"],
            "name": result["name"],
        }))
    except Exception as e:
        logger.error(f"声音克隆失败: {e}")
        await ws.send(json.dumps({
            "type": "voice_clone_result",
            "success": False,
            "error": str(e),
        }))


async def handle_voice_generate(ws: WebSocketServerProtocol, data: dict):
    """处理 AI 音线生成请求"""
    try:
        description = data.get("description", "")

        if not description:
            await ws.send(json.dumps({
                "type": "voice_generate_result",
                "success": False,
                "error": "请提供音线描述",
            }))
            return

        result = voice_generator.generate(description)

        # 注册到 TTS Router
        tts_router.register_custom_voice(result["voice_id"], result["config"])

        # 生成试听音频
        preview_audio = await tts_router.synthesize(
            result["config"].get("preview_text", "你好，这是试听音频。"),
            result["voice_id"],
            user_settings,
        )

        await ws.send(json.dumps({
            "type": "voice_generate_result",
            "success": True,
            "voice_id": result["voice_id"],
            "name": result["name"],
            "description": result["description"],
            "matched_features": result["matched_features"],
            "preview_audio": base64.b64encode(preview_audio).decode() if preview_audio else None,
        }))
    except Exception as e:
        logger.error(f"音线生成失败: {e}")
        await ws.send(json.dumps({
            "type": "voice_generate_result",
            "success": False,
            "error": str(e),
        }))


async def send_text_response(ws: WebSocketServerProtocol, message_id: str, text: str):
    """发送流式文本回复，可选附带 TTS 音频"""
    # 流式发送文本
    for i in range(0, len(text), 10):
        chunk = text[i:i+10]
        await ws.send(json.dumps({
            "type": "agent_response",
            "id": message_id,
            "content": chunk,
            "status": "streaming",
            "persona_state": "speaking",
        }))
        await asyncio.sleep(0.03)

    # 文本发送完成
    await ws.send(json.dumps({
        "type": "agent_response",
        "id": message_id,
        "content": "",
        "status": "done",
        "persona_state": "speaking",
    }))

    # 如果启用了语音，生成 TTS 音频并发送（失败不影响文本回复）
    if user_settings.get("voice.enabled", False):
        try:
            voice_id = user_settings.get("voice.preset_id", "sweet_female")
            audio_data = await tts_router.synthesize(text, voice_id, user_settings)
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                await ws.send(json.dumps({
                    "type": "agent_audio",
                    "id": message_id,
                    "audio": audio_b64,
                    "persona_state": "speaking",
                }))
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")

    # 语音播放完毕，回到 idle
    await ws.send(json.dumps({
        "type": "agent_response",
        "id": message_id,
        "content": "",
        "status": "done",
        "persona_state": "idle",
    }))


def format_capability_results(intent: str, results: list) -> str:
    """根据 capability 执行结果生成自然语言回复"""
    if not results:
        return "操作未能执行，请重试。"

    first = results[0]
    if not first.get("success"):
        return f"操作失败：{first.get('error', '未知错误')}"

    data = first.get("data", {})

    if intent == "file_list":
        entries = data.get("entries", [])
        if not entries:
            return "目录为空，没有找到文件。"
        lines = [f"扫描完成，找到 {len(entries)} 个文件/目录：\n"]
        for entry in entries[:20]:  # 最多显示 20 个
            icon = "📁" if entry.get("is_dir") else "📄"
            size = entry.get("size", 0)
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.1f}MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size}B"
            lines.append(f"{icon} {entry.get('name', '?')} ({size_str})")
        if len(entries) > 20:
            lines.append(f"\n...还有 {len(entries) - 20} 个文件")
        return "\n".join(lines)

    elif intent == "file_delete":
        entries = data.get("entries", [])
        if not entries:
            return "目录为空，没有需要清理的文件。"
        # 找出可清理的文件（临时文件、大文件等）
        cleanable = [e for e in entries if not e.get("is_dir") and (
            e.get("name", "").endswith((".tmp", ".temp", ".log", ".bak"))
            or e.get("size", 0) > 100 * 1024 * 1024  # > 100MB
        )]
        if not cleanable:
            return f"扫描了 {len(entries)} 个文件，没有发现明显的垃圾文件。"
        total_size = sum(e.get("size", 0) for e in cleanable)
        lines = [f"找到 {len(cleanable)} 个可清理文件，共 {total_size / 1024 / 1024:.1f}MB：\n"]
        for entry in cleanable[:10]:
            size = entry.get("size", 0)
            lines.append(f"• {entry.get('name', '?')} ({size / 1024:.1f}KB)")
        lines.append("\n请确认是否要删除这些文件？")
        return "\n".join(lines)

    elif intent == "file_read":
        content = data.get("content", "")
        if len(content) > 500:
            content = content[:500] + "\n...(内容已截断)"
        return f"文件内容：\n```\n{content}\n```"

    elif intent == "app_launch":
        return f"已启动应用！"

    elif intent == "app_close":
        return f"已关闭应用！"

    elif intent == "app_list":
        processes = data.get("processes", "[]")
        try:
            procs = json.loads(processes) if isinstance(processes, str) else processes
            if isinstance(procs, list):
                lines = [f"当前有 {len(procs)} 个运行中的进程：\n"]
                for p in procs[:15]:
                    title = p.get("MainWindowTitle", "")
                    name = p.get("ProcessName", "?")
                    if title:
                        lines.append(f"• {name} — {title}")
                return "\n".join(lines)
        except (json.JSONDecodeError, TypeError):
            pass
        return f"获取进程列表成功。"

    elif intent == "system_info":
        os_name = data.get("os", "Unknown")
        version = data.get("version", "")
        hostname = data.get("hostname", "")
        arch = data.get("arch", "")
        return f"系统信息：\n• OS: {os_name}\n• 版本: {version}\n• 主机名: {hostname}\n• 架构: {arch}"

    elif intent == "system_lock":
        return "系统已锁定！"

    return "操作执行完成。"


async def handle_confirm_response(ws: WebSocketServerProtocol, data: dict):
    confirmed = data.get("confirmed", False)
    logger.info(f"用户确认: {confirmed}")


async def handler(ws: WebSocketServerProtocol):
    connected_clients.add(ws)
    logger.info(f"客户端已连接 (共 {len(connected_clients)} 个)")
    try:
        async for message in ws:
            await handle_message(ws, message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(ws)
        logger.info(f"客户端已断开 (共 {len(connected_clients)} 个)")


async def main():
    config.ensure_dirs()
    logger.info(f"Auralis Agent 启动中...")
    logger.info(f"WebSocket 监听: ws://{config.WS_HOST}:{config.WS_PORT}")

    async with websockets.serve(handler, config.WS_HOST, config.WS_PORT):
        logger.info("Agent 就绪，等待连接...")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
