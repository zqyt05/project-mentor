"""API 路由包。

按业务模块拆分为四组路由：项目 / 任务 / 答疑 / 复盘，
在 `app.main` 中统一注册。
"""

from app.api import chat, project, review, task

__all__ = ["chat", "project", "review", "task"]
