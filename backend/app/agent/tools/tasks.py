"""任务工具：AI 通过 Tool Calling 操作用户任务（只走 TaskService，不碰数据库）。"""
from datetime import date

from app.agent.base import AgentContext, ToolResult
from app.services import task as task_service


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class CreateTaskTool:
    name = "create_task"
    description = "创建一条新任务。用户要求添加待办、提醒、学习任务等时使用。"
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "任务标题"},
            "description": {"type": "string", "description": "任务详细描述（可选）"},
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "优先级（可选，默认 medium）",
            },
            "due_date": {"type": "string", "description": "截止日期 YYYY-MM-DD（可选）"},
        },
        "required": ["title"],
    }

    async def execute(
        self,
        ctx: AgentContext,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        due_date: str | None = None,
    ) -> ToolResult:
        try:
            task = await task_service.create_task(
                ctx.db,
                ctx.user_id,
                title=title,
                description=description,
                priority=priority if priority in ("high", "medium", "low") else "medium",
                due_date=_parse_date(due_date),
            )
            return ToolResult(
                success=True,
                data={"id": task.id, "title": task.title, "status": task.status, "priority": task.priority},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class ListTasksTool:
    name = "list_tasks"
    description = "查询用户的任务列表，可按状态或优先级筛选。用户询问自己的任务、待办时使用。"
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "description": "按状态筛选（可选）",
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "按优先级筛选（可选）",
            },
        },
        "required": [],
    }

    async def execute(
        self,
        ctx: AgentContext,
        status: str | None = None,
        priority: str | None = None,
    ) -> ToolResult:
        try:
            tasks = await task_service.list_tasks(ctx.db, ctx.user_id, status, priority)
            return ToolResult(
                success=True,
                data={
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "status": t.status,
                            "priority": t.priority,
                            "due_date": t.due_date.isoformat() if t.due_date else None,
                        }
                        for t in tasks
                    ]
                },
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class UpdateTaskTool:
    name = "update_task"
    description = "修改用户的任务（标题/状态/优先级/截止日期）。用户要求完成任务、修改任务时使用。"
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "任务 ID（必填）"},
            "title": {"type": "string", "description": "新标题（可选）"},
            "status": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "description": "新状态（可选）",
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "新优先级（可选）",
            },
            "due_date": {"type": "string", "description": "新截止日期 YYYY-MM-DD（可选）"},
        },
        "required": ["task_id"],
    }

    async def execute(
        self,
        ctx: AgentContext,
        task_id: int,
        title: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
    ) -> ToolResult:
        try:
            fields: dict = {}
            if title is not None:
                fields["title"] = title
            if status in ("todo", "in_progress", "done"):
                fields["status"] = status
            if priority in ("high", "medium", "low"):
                fields["priority"] = priority
            if due_date is not None:
                fields["due_date"] = _parse_date(due_date)
            if not fields:
                return ToolResult(success=False, error="没有提供任何要修改的字段")
            task = await task_service.update_task(ctx.db, ctx.user_id, task_id, **fields)
            return ToolResult(
                success=True,
                data={"id": task.id, "title": task.title, "status": task.status, "priority": task.priority},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class DeleteTaskTool:
    name = "delete_task"
    description = "删除用户的一条任务。用户要求删除、取消任务时使用。"
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "要删除的任务 ID（必填）"},
        },
        "required": ["task_id"],
    }

    async def execute(self, ctx: AgentContext, task_id: int) -> ToolResult:
        try:
            await task_service.delete_task(ctx.db, ctx.user_id, task_id)
            return ToolResult(success=True, data={"deleted": task_id})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
