"""Auralis Agent WebSocket 服务端"""

import asyncio
import base64
import json
import logging
import signal
import uuid
import websockets
from websockets.server import WebSocketServerProtocol

from config import config
from intent.parser import IntentParser
from model.router import ModelRouter
from prompts.system import build_system_prompt
from tools.functions import TOOLS
from settings.ai_handler import (
    handle_settings_change,
    format_settings_reply, format_change_reply,
)
from tts.router import TTSRouter
from tts.clone import VoiceCloner
from tts.generator import VoiceGenerator
from memory.conversation_store import ConversationStore
from memory.audit_store import AuditStore
from memory.event_store import EventStore
from memory.memory_layer import MemoryLayer
from planner.dag import TaskGraph, TaskNode, build_planning_prompt, parse_planning_result
from planner.executor import TaskExecutor
from policy.risk_engine import RiskEngine
from policy.confirmation import ConfirmationManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("auralis.agent")

connected_clients: set[WebSocketServerProtocol] = set()
intent_parser = IntentParser()
model_router = ModelRouter()
tts_router = TTSRouter()
voice_cloner = VoiceCloner()
voice_generator = VoiceGenerator()
conversation_store = ConversationStore()
audit_store = AuditStore()
event_store = EventStore()
memory_layer = MemoryLayer()
risk_engine = RiskEngine()
confirm_manager = ConfirmationManager()

# 等待前端返回 capability 执行结果的回调
pending_results: dict[str, asyncio.Future] = {}

# 用户设置缓存（前端同步过来的）
user_settings: dict = {}

# WebSocket 连接 → session_id 映射
ws_session_map: dict[int, str] = {}
MAX_HISTORY = 20  # 每个 session 加载的历史消息数


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
        elif msg_type == "voice_preview":
            await handle_voice_preview(ws, data)
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
    session_id = _get_session_id(ws)
    logger.info(f"用户消息: {content}")

    # 记录用户输入事件（通过记忆系统）
    memory_layer.record_user_action("chat_input", {"content": content}, session_id=session_id)

    # 1. 先尝试规则匹配（快速路径）
    result = intent_parser.parse(content)
    logger.info(f"规则匹配: {result['intent']}")

    # 明确的 UI 操作直接处理，不走 LLM
    if result["intent"] in ("settings_open", "settings_close"):
        if result["intent"] == "settings_open":
            await ws.send(json.dumps({"type": "agent_command", "command": "open-settings"}))
            await send_text_response(ws, message_id, "好的，已为你打开设置面板。")
        else:
            await ws.send(json.dumps({"type": "agent_command", "command": "close-settings"}))
            await send_text_response(ws, message_id, "设置面板已关闭。")
        return

    # 设置查询/修改也可以走规则快速路径
    if result["intent"] == "settings_query":
        await _handle_settings_query(ws, message_id)
        return

    if result["intent"] == "settings_change":
        await _handle_settings_change(ws, message_id, result)
        return

    # 有明确 capability 的操作也走规则路径（如"打开记事本"、"查看系统信息"）
    if result["intent"] != "unknown" and result["capabilities"]:
        # 立即发送 capability 请求（不阻塞），同时后台流式输出回复文本
        if result["reply"]:
            asyncio.create_task(send_text_response(ws, message_id, result["reply"]))
        await _execute_capabilities(ws, message_id, result)
        return

    # 2. 规则匹配失败或 unknown → 调用 LLM
    await _handle_with_llm(ws, message_id, content)


async def _handle_settings_query(ws: WebSocketServerProtocol, message_id: str):
    """处理设置查询（规则路径）"""
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


async def _handle_settings_change(ws: WebSocketServerProtocol, message_id: str, result: dict):
    """处理设置修改（规则路径）"""
    changes = result.get("settings_changes", [])
    if not changes:
        await send_text_response(ws, message_id, "请告诉我你想修改什么设置。")
        return

    change_result = handle_settings_change(changes)
    needs_confirm = [r for r in change_result["results"] if r.get("needs_confirm")]
    ready_changes = [r for r in change_result["results"] if r.get("success")]

    if needs_confirm:
        confirm_msg = "\n".join(r["message"] for r in needs_confirm)
        await send_text_response(ws, message_id, f"需要你的确认：\n{confirm_msg}")
        return

    if ready_changes:
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

    reply = format_change_reply(change_result)
    await send_text_response(ws, message_id, reply)


async def _execute_capabilities(ws: WebSocketServerProtocol, message_id: str, result: dict):
    """执行 capability 操作（含风险评估：低/中风险直接执行，高风险暂停确认）"""
    # 风险评估：分离安全和危险操作
    safe_caps = []
    dangerous_caps = []
    for cap in result["capabilities"]:
        cap_type = cap.get("capability", {}).get("type", "unknown")
        cap_payload = cap.get("capability", {}).get("payload", {})
        risk_level, risk_score = risk_engine.evaluate(cap_type, cap_payload)
        if risk_level.value == "high":
            dangerous_caps.append((cap, cap_type, cap_payload, risk_level))
        else:
            safe_caps.append(cap)

    # 先执行安全操作
    if safe_caps:
        safe_result = dict(result)
        safe_result["capabilities"] = safe_caps
        await _execute_capability_batch(ws, message_id, safe_result)

    # 高风险操作暂停确认
    if dangerous_caps:
        for cap, cap_type, cap_payload, risk_level in dangerous_caps:
            confirm_info = confirm_manager.decide(cap_type, cap_payload, risk_level)
            await send_text_response(ws, message_id, confirm_info.message)
        return  # 高风险操作等待用户确认


async def _execute_capability_batch(ws: WebSocketServerProtocol, message_id: str, result: dict):
    """执行一批 capability 操作（已通过风险评估）"""
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"发送 capability 请求: {request_id}, {len(result['capabilities'])} 个操作")

    future = asyncio.get_event_loop().create_future()
    pending_results[request_id] = future

    await ws.send(json.dumps({
        "type": "capability_request",
        "request_id": request_id,
        "capabilities": result["capabilities"],
    }))

    # 用后台任务等待结果，不阻塞消息处理循环
    # 否则 capability_result 会被缓冲但无法处理，导致 handler 死锁超时
    asyncio.create_task(_wait_capability_result(ws, message_id, request_id, result, future))


async def _wait_capability_result(
    ws: WebSocketServerProtocol, message_id: str,
    request_id: str, result: dict, future: asyncio.Future,
):
    """后台等待 capability 执行结果并发送回复"""
    try:
        import time
        start_time = time.monotonic()
        cap_results = await asyncio.wait_for(future, timeout=30.0)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # 审计日志（每个 capability 对应一个结果）
        session_id = _get_session_id(ws)
        for i, cap in enumerate(result["capabilities"]):
            cap_type = cap.get("capability", {}).get("type", "unknown")
            cap_result = cap_results[i] if i < len(cap_results) else {"success": False, "error": "结果缺失"}
            audit_store.log(
                capability_type=cap_type,
                session_id=session_id,
                result="success" if cap_result.get("success") else "error",
                error_message=cap_result.get("error"),
                duration_ms=duration_ms,
            )

        reply = format_capability_results(result["intent"], cap_results)
        await send_text_response(ws, message_id, reply)
    except asyncio.TimeoutError:
        # 超时也记录审计
        for cap in result["capabilities"]:
            cap_type = cap.get("capability", {}).get("type", "unknown")
            audit_store.log(
                capability_type=cap_type,
                session_id=_get_session_id(ws),
                result="timeout",
                error_message="操作执行超时",
            )
        await send_text_response(ws, message_id, "操作执行超时，请重试。")
    finally:
        pending_results.pop(request_id, None)


async def _handle_with_llm(ws: WebSocketServerProtocol, message_id: str, user_input: str):
    """使用 LLM 处理消息（支持 Function Calling）"""
    # 发送思考状态
    await ws.send(json.dumps({
        "type": "agent_response",
        "id": message_id,
        "content": "",
        "status": "thinking",
        "persona_state": "thinking",
    }))

    # 获取或创建 session
    session_id = _get_session_id(ws)

    # 从持久化存储加载历史
    history = conversation_store.get_history(session_id, limit=MAX_HISTORY)

    # 构建系统提示词
    locale = user_settings.get("locale", "zh-CN")
    system_prompt = build_system_prompt(locale, user_settings)

    # 注入记忆上下文
    memory_context = memory_layer.get_context_for_llm(user_input)
    if memory_context:
        system_prompt += f"\n\n## 记忆上下文\n{memory_context}"

    # 组装消息
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    try:
        # 调用 LLM（带 tools）
        llm_result = await model_router.chat(
            messages, user_settings, stream=False, tools=TOOLS,
        )

        # 解析 LLM 返回
        if isinstance(llm_result, dict) and llm_result.get("tool_calls"):
            # LLM 要求调用工具
            await _handle_llm_tool_calls(ws, message_id, user_input, llm_result, session_id)
        else:
            # 纯文本回复
            reply = llm_result if isinstance(llm_result, str) else str(llm_result)
            await send_text_response(ws, message_id, reply)
            # 持久化对话（批量写入，保证原子性）
            conversation_store.save_messages(session_id, [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": reply},
            ])

    except Exception as e:
        logger.error(f"LLM 调用失败: {e}", exc_info=True)
        # 降级：回退到规则匹配的 unknown 提示
        await send_text_response(ws, message_id,
            f"抱歉，AI 模型暂时不可用（{type(e).__name__}）。\n\n"
            "你可以试试以下命令：\n"
            "• 扫描桌面文件\n"
            "• 打开记事本\n"
            "• 查看系统信息\n"
            "• 列出运行中的应用\n"
            "• 打开设置\n"
            "• 把语言改成中文\n"
            "• 我现在的设置是什么"
        )


async def _handle_llm_tool_calls(
    ws: WebSocketServerProtocol, message_id: str,
    user_input: str, llm_result: dict, session_id: str,
):
    """处理 LLM 返回的 tool_calls（支持 DAG 并行执行）"""
    tool_calls = llm_result["tool_calls"]
    assistant_content = llm_result.get("content") or ""

    # 如果 LLM 有文本回复，先发送
    if assistant_content:
        await send_text_response(ws, message_id, assistant_content)

    # 持久化用户消息和 assistant 回复（含 tool_calls）
    tool_calls_for_storage = [
        {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
        for tc in tool_calls
    ]
    conversation_store.save_messages(session_id, [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": assistant_content, "tool_calls": tool_calls_for_storage},
    ])

    # 单个 tool_call 直接执行（保持原有逻辑）
    if len(tool_calls) == 1:
        await _execute_single_tool_call(ws, message_id, tool_calls[0], session_id)
    else:
        # 多个 tool_call → 使用 DAG 执行引擎（并行执行无依赖的任务）
        await _execute_tool_calls_dag(ws, message_id, tool_calls, session_id)

    # 让 LLM 基于工具执行结果生成最终回复
    await _llm_summarize_results(ws, message_id, session_id)


async def _execute_single_tool_call(
    ws: WebSocketServerProtocol, message_id: str,
    tc: dict, session_id: str,
):
    """执行单个 tool_call"""
    tool_name = tc["name"]
    try:
        args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
    except json.JSONDecodeError:
        args = {}

    logger.info(f"执行工具: {tool_name}({args})")

    import time
    start_time = time.monotonic()
    tool_result = await _execute_tool(tool_name, args, ws, message_id)
    duration_ms = int((time.monotonic() - start_time) * 1000)

    audit_store.log(
        capability_type=tool_name,
        session_id=session_id,
        risk_level="low",
        result="success" if tool_result.get("success") else "error",
        error_message=tool_result.get("error"),
        duration_ms=duration_ms,
        details={"args": args},
    )

    content = json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result)
    conversation_store.save_message(session_id, "tool", content, tool_call_id=tc["id"])


async def _execute_tool_calls_dag(
    ws: WebSocketServerProtocol, message_id: str,
    tool_calls: list[dict], session_id: str,
):
    """使用 DAG 引擎并行执行多个 tool_calls"""
    # 构建 TaskGraph（tool_calls 之间无显式依赖，可并行执行）
    graph = TaskGraph()

    for tc in tool_calls:
        try:
            args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
        except json.JSONDecodeError:
            args = {}

        node = TaskNode(
            name=f"{tc['name']}_{tc['id'][:8]}",
            tool_name=tc["name"],
            args=args,
            task_id=tc["id"],
        )
        graph.add_node(node)

    # 发送初始进度
    await ws.send(json.dumps({
        "type": "task_progress",
        "graph": graph.to_dict(),
    }))

    # 进度回调
    async def on_progress(progress: dict):
        await ws.send(json.dumps({"type": "task_progress", "graph": progress}))

    # 创建执行器
    async def tool_executor(tool_name: str, args: dict) -> dict:
        return await _execute_tool(tool_name, args, ws, message_id)

    executor = TaskExecutor(tool_executor=tool_executor, on_progress=on_progress)
    await executor.execute(graph)

    # 审计日志 + 持久化结果（使用每个节点独立的 duration_ms）
    for node in graph.nodes.values():
        result = node.result or {"success": False, "error": node.error}
        audit_store.log(
            capability_type=node.tool_name,
            session_id=session_id,
            risk_level="low",
            result="success" if node.status.value == "completed" else "error",
            error_message=node.error,
            duration_ms=node.duration_ms,
            details={"args": node.args},
        )
        content = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
        conversation_store.save_message(session_id, "tool", content, tool_call_id=node.id)

    # 发送完成状态
    await ws.send(json.dumps({"type": "task_progress", "graph": graph.to_dict(), "status": "done"}))


async def _execute_tool(tool_name: str, args: dict, ws: WebSocketServerProtocol, message_id: str) -> dict:
    """执行单个工具调用"""
    if tool_name == "settings_query":
        request_id = str(uuid.uuid4())[:8]
        future = asyncio.get_event_loop().create_future()
        pending_results[request_id] = future
        await ws.send(json.dumps({"type": "settings_query", "request_id": request_id}))
        try:
            result = await asyncio.wait_for(future, timeout=10.0)
            return {"success": True, "settings": result.get("settings", [])}
        except asyncio.TimeoutError:
            return {"success": False, "error": "查询超时"}
        finally:
            pending_results.pop(request_id, None)

    elif tool_name == "settings_change":
        changes = args.get("changes", [])
        if not changes:
            return {"success": False, "error": "未提供修改内容"}
        change_result = handle_settings_change(changes)
        ready = [r for r in change_result["results"] if r.get("success")]
        needs_confirm = [r for r in change_result["results"] if r.get("needs_confirm")]

        # 如果有需要确认的项，包含在结果中让 LLM 告知用户
        if needs_confirm and not ready:
            return {
                "success": False,
                "needs_confirm": [r["message"] for r in needs_confirm],
                "error": "以下设置需要确认：" + "；".join(r["message"] for r in needs_confirm),
            }

        if not ready:
            return {"success": False, "results": change_result["results"]}
        # 发给前端应用
        request_id = str(uuid.uuid4())[:8]
        future = asyncio.get_event_loop().create_future()
        pending_results[request_id] = future
        await ws.send(json.dumps({
            "type": "settings_change",
            "request_id": request_id,
            "changes": [{"key": r["key"], "value": r["value"]} for r in ready],
        }))
        try:
            apply_result = await asyncio.wait_for(future, timeout=10.0)
            return {"success": True, "applied": ready, "result": apply_result}
        except asyncio.TimeoutError:
            return {"success": False, "error": "修改超时"}
        finally:
            pending_results.pop(request_id, None)

    elif tool_name == "execute_capability":
        cap_type = args.get("capability_type", "")
        payload = args.get("payload", {})
        cap_id = str(uuid.uuid4())[:8]
        capability = {"type": cap_type, "payload": payload}

        future = asyncio.get_event_loop().create_future()
        pending_results[cap_id] = future
        await ws.send(json.dumps({
            "type": "capability_request",
            "request_id": cap_id,
            "capabilities": [{"id": cap_id, "capability": capability}],
        }))
        try:
            results = await asyncio.wait_for(future, timeout=30.0)
            return {"success": True, "results": results}
        except asyncio.TimeoutError:
            return {"success": False, "error": "操作超时"}
        finally:
            pending_results.pop(cap_id, None)

    elif tool_name == "open_settings":
        await ws.send(json.dumps({"type": "agent_command", "command": "open-settings"}))
        return {"success": True, "message": "设置面板已打开"}

    elif tool_name == "close_settings":
        await ws.send(json.dumps({"type": "agent_command", "command": "close-settings"}))
        return {"success": True, "message": "设置面板已关闭"}

    return {"success": False, "error": f"未知工具: {tool_name}"}


async def _llm_summarize_results(ws: WebSocketServerProtocol, message_id: str, session_id: str):
    """让 LLM 基于工具执行结果生成自然语言回复"""
    locale = user_settings.get("locale", "zh-CN")
    system_prompt = build_system_prompt(locale, user_settings)

    # 从 DB 加载历史
    history = conversation_store.get_history(session_id, limit=MAX_HISTORY)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    # 添加 synthetic user prompt（不持久化，仅用于本次 LLM 调用）
    summarize_prompt = "请根据以上工具执行结果，用简洁的中文回复用户。"
    messages.append({"role": "user", "content": summarize_prompt})

    try:
        reply = await model_router.chat(messages, user_settings, stream=False)
        # 处理可能的 dict 返回（LLM 不应再调用工具，但防御性处理）
        if isinstance(reply, dict):
            reply = reply.get("content") or ""
        if isinstance(reply, str) and reply:
            await send_text_response(ws, message_id, reply)
            conversation_store.save_message(session_id, "assistant", reply)
        else:
            # LLM 未返回有效回复，发送兜底文本
            fallback = "操作已完成。"
            await send_text_response(ws, message_id, fallback)
            conversation_store.save_message(session_id, "assistant", fallback)
    except Exception as e:
        logger.warning(f"LLM 总结失败: {e}")
        # 异常时发送兜底文本，确保用户总能收到反馈
        fallback = "操作已完成。"
        await send_text_response(ws, message_id, fallback)
        conversation_store.save_message(session_id, "assistant", fallback)


def _get_session_id(ws: WebSocketServerProtocol) -> str:
    """获取或创建 WebSocket 连接对应的 session_id"""
    ws_key = id(ws)
    if ws_key not in ws_session_map:
        ws_session_map[ws_key] = str(uuid.uuid4())[:12]
    return ws_session_map[ws_key]


async def handle_capability_result(ws: WebSocketServerProtocol, data: dict):
    """处理前端返回的 capability 执行结果"""
    request_id = data.get("request_id")
    logger.info(f"收到 capability 结果: request_id={request_id}")

    # 防御性处理：前端返回 needs_confirmation 时（不应发生，风险等级已对齐）
    needs_confirm = data.get("needs_confirmation")
    if needs_confirm:
        logger.warning(f"收到 needs_confirmation（风险等级不一致）: {needs_confirm}")
        # 将 needs_confirmation 当作错误结果
        cap_type = needs_confirm.get("capability_type", "unknown")
        future = pending_results.get(request_id)
        if future and not future.done():
            future.set_result([{
                "id": str(uuid.uuid4())[:8],
                "success": False,
                "error": f"操作需要确认：{needs_confirm.get('message')}",
                "needs_confirmation": needs_confirm,
            }])
        pending_results.pop(request_id, None)
        return

    results = data.get("results", [])

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


async def handle_voice_preview(ws: WebSocketServerProtocol, data: dict):
    """处理音线试听请求：用指定音线合成一段短音频（含重试）"""
    voice_id = data.get("voice_id", "neutral")
    preview_text = data.get("text", "你好，这是试听音频。很高兴认识你！")
    logger.info(f"音线试听请求: voice_id={voice_id}")

    audio_data = None
    last_error = None
    for attempt in range(3):
        try:
            audio_data = await tts_router.synthesize(preview_text, voice_id, user_settings)
            if audio_data:
                break
            # None 表示持久性失败（引擎不可用），不重试
            last_error = "TTS 合成返回空"
            break
        except Exception as e:
            last_error = str(e)
            logger.warning(f"音线试听第 {attempt + 1} 次失败: {e}")
            if attempt < 2:
                import asyncio
                await asyncio.sleep(0.5)

    if audio_data:
        audio_b64 = base64.b64encode(audio_data).decode()
        logger.info(f"音线试听合成成功: voice_id={voice_id}, audio_size={len(audio_data)} bytes")
        await ws.send(json.dumps({
            "type": "voice_preview_result",
            "success": True,
            "voice_id": voice_id,
            "audio": audio_b64,
        }))
    else:
        logger.error(f"音线试听最终失败: voice_id={voice_id}, error={last_error}")
        await ws.send(json.dumps({
            "type": "voice_preview_result",
            "success": False,
            "voice_id": voice_id,
            "error": last_error,
        }))


async def send_text_response(ws: WebSocketServerProtocol, message_id: str, text: str):
    """发送流式文本回复，可选附带 TTS 音频"""
    # 使用新 ID 生成 agent 回复（避免与 user 消息 ID 冲突）
    agent_msg_id = f"agent_{message_id}"
    # 流式发送文本
    for i in range(0, len(text), 10):
        chunk = text[i:i+10]
        await ws.send(json.dumps({
            "type": "agent_response",
            "id": agent_msg_id,
            "content": chunk,
            "status": "streaming",
            "persona_state": "speaking",
        }))
        await asyncio.sleep(0.03)

    # 文本发送完成
    await ws.send(json.dumps({
        "type": "agent_response",
        "id": agent_msg_id,
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
        # 清理 session 映射（对话历史已持久化到 DB，无需清理）
        ws_session_map.pop(id(ws), None)
        logger.info(f"客户端已断开 (共 {len(connected_clients)} 个)")


async def main():
    config.ensure_dirs()
    # 启动时清理过期对话（30 天）
    conversation_store.cleanup_old(days=30)
    logger.info(f"Auralis Agent 启动中...")
    logger.info(f"WebSocket 监听: ws://{config.WS_HOST}:{config.WS_PORT}")

    # 创建停止事件
    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("收到退出信号，正在停止...")
        stop_event.set()

    # 注册信号处理（Windows 上 SIGTERM 可能不可用，使用 SIGBREAK）
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler，使用传统方式
            pass

    async with websockets.serve(handler, config.WS_HOST, config.WS_PORT):
        logger.info("Agent 就绪，等待连接...")
        # 等待停止信号
        await stop_event.wait()
        logger.info("Agent 正在关闭...")

        # 关闭所有客户端连接
        for client in connected_clients.copy():
            try:
                await client.close()
            except Exception:
                pass
        connected_clients.clear()

    logger.info("Agent 已停止")


if __name__ == "__main__":
    asyncio.run(main())
