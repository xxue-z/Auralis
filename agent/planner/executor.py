"""DAG 执行引擎 — 按拓扑顺序执行任务图"""

import asyncio
import logging
import time
from typing import Any, Callable, Awaitable

from planner.dag import TaskGraph, TaskNode, TaskStatus

logger = logging.getLogger("auralis.planner")

# 工具执行器类型：async (tool_name, args) → result dict
ToolExecutor = Callable[[str, dict], Awaitable[dict]]


class TaskExecutor:
    """DAG 执行引擎"""

    def __init__(
        self,
        tool_executor: ToolExecutor,
        on_progress: Callable[[dict], Awaitable[None]] | None = None,
    ):
        """
        Args:
            tool_executor: 异步回调，执行单个工具调用
            on_progress: 进度回调，每次状态变化时调用
        """
        self.tool_executor = tool_executor
        self.on_progress = on_progress

    async def execute(self, graph: TaskGraph) -> TaskGraph:
        """
        按拓扑顺序执行 DAG 中的所有任务。

        - 无依赖的任务并行执行
        - 有依赖的任务等待前置完成
        - 任务失败时下游自动跳过

        Returns:
            执行完成的 TaskGraph（结果写入各节点）
        """
        if not graph.nodes:
            return graph

        # 检测循环依赖
        if graph.detect_cycle():
            logger.error("任务图存在循环依赖")
            for node in graph.nodes.values():
                node.status = TaskStatus.FAILED
                node.error = "任务图存在循环依赖"
            await self._report_progress(graph)
            return graph

        # 标记初始就绪任务
        for node in graph.nodes.values():
            if not node.dependencies:
                node.status = TaskStatus.READY

        await self._report_progress(graph)

        # 执行循环
        while not graph.is_complete():
            ready = graph.get_ready_tasks()
            if not ready:
                # 没有可执行的任务（死锁或全部完成）
                break

            # 并行执行所有就绪任务
            tasks = [self._execute_node(graph, node) for node in ready]
            await asyncio.gather(*tasks)

        return graph

    async def _execute_node(self, graph: TaskGraph, node: TaskNode) -> None:
        """执行单个任务节点"""
        graph.update_status(node.id, TaskStatus.RUNNING)
        await self._report_progress(graph)

        start_time = time.monotonic()
        try:
            # 解析参数中的变量引用
            resolved_args = graph.resolve_args(node.args, node.id)
            logger.info(f"执行任务: {node.name} ({node.tool_name})")

            # 调用工具
            result = await self.tool_executor(node.tool_name, resolved_args)

            # 标记完成
            graph.mark_completed(node.id, result)
            logger.info(f"任务完成: {node.name}")

        except asyncio.TimeoutError:
            error = f"任务执行超时: {node.name}"
            logger.warning(error)
            graph.mark_failed(node.id, error)

        except Exception as e:
            error = f"任务执行失败: {node.name} — {type(e).__name__}: {e}"
            logger.error(error, exc_info=True)
            graph.mark_failed(node.id, error)

        node.duration_ms = int((time.monotonic() - start_time) * 1000)
        await self._report_progress(graph)

    async def _report_progress(self, graph: TaskGraph) -> None:
        """发送进度更新"""
        if self.on_progress:
            try:
                await self.on_progress(graph.to_dict())
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")


def summarize_results(graph: TaskGraph) -> str:
    """根据 DAG 执行结果生成自然语言摘要"""
    completed = []
    failed = []
    skipped = []

    for node in graph.nodes.values():
        if node.status == TaskStatus.COMPLETED:
            completed.append(node)
        elif node.status == TaskStatus.FAILED:
            failed.append(node)
        elif node.status == TaskStatus.SKIPPED:
            skipped.append(node)

    lines = []

    if completed:
        lines.append(f"✅ 成功完成 {len(completed)} 个任务：")
        for node in completed:
            lines.append(f"  • {node.name}")

    if failed:
        lines.append(f"\n❌ {len(failed)} 个任务失败：")
        for node in failed:
            lines.append(f"  • {node.name}: {node.error}")

    if skipped:
        lines.append(f"\n⏭️ {len(skipped)} 个任务被跳过：")
        for node in skipped:
            lines.append(f"  • {node.name}")

    if not lines:
        return "任务执行完成。"

    # 添加执行统计
    total = len(graph.nodes)
    lines.append(f"\n📊 共 {total} 个任务：{len(completed)} 成功 / {len(failed)} 失败 / {len(skipped)} 跳过")

    return "\n".join(lines)
