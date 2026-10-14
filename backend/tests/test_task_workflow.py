"""任务拆解、顺序门禁与进度计算测试。

这三块是项目最核心的确定性逻辑：DDL 累加算错、门禁失效、进度统计偏差，
在界面上都很难靠肉眼发现，但会直接破坏「按顺序推进」的学习体验。
"""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import Project, ProjectSource, TaskStatus
from app.services.project_service import compute_progress, persist_decomposition

# 两个阶段共 3 个任务，建议天数 1 / 3 / 2
DECOMPOSITION = [
    {
        "name": "阶段一 · 准备",
        "description": "准备环境",
        "is_milestone": True,
        "tasks": [
            {
                "name": "任务A",
                "description": "a",
                "knowledge_points": ["k1", "k2"],
                "deliverable_criteria": "标准A",
                "ddl_days": 1,
            },
            {
                "name": "任务B",
                "description": "b",
                "knowledge_points": [],
                "deliverable_criteria": "标准B",
                "ddl_days": 3,
            },
        ],
    },
    {
        "name": "阶段二 · 产出",
        "description": "做出成果",
        "is_milestone": True,
        "tasks": [
            {
                "name": "任务C",
                "description": "c",
                "knowledge_points": ["k3"],
                "deliverable_criteria": "标准C",
                "ddl_days": 2,
            },
        ],
    },
]


def make_project(db: Session, name: str = "测试项目") -> Project:
    """创建一个最小可用的项目记录。"""
    project = Project(
        name=name,
        source=ProjectSource.CUSTOM,
        domain="测试方向",
        difficulty="入门",
    )
    db.add(project)
    db.flush()
    return project


def build_tasks(db: Session, statuses: list[str]) -> tuple[Project, list]:
    """建项目 + 落库拆解结果 + 按传入顺序设置任务状态。"""
    project = make_project(db)
    persist_decomposition(db, project, DECOMPOSITION)
    db.commit()

    tasks = sorted(project.tasks, key=lambda item: item.order_index)
    for task, status in zip(tasks, statuses, strict=True):
        task.status = status
    db.commit()
    return project, tasks


class TestDecompositionPersistence:
    """拆解结果落库：顺序、阶段关联与 DDL 累加。"""

    def test_tasks_persisted_in_order(self, db: Session) -> None:
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()

        tasks = sorted(project.tasks, key=lambda item: item.order_index)
        assert [task.name for task in tasks] == ["任务A", "任务B", "任务C"]

    def test_order_index_is_continuous_across_stages(self, db: Session) -> None:
        """order_index 必须跨阶段连续，否则顺序门禁会失效。"""
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()

        orders = sorted(task.order_index for task in project.tasks)
        assert orders == [0, 1, 2]

    def test_due_date_is_cumulative(self, db: Session) -> None:
        """DDL = 项目开始日 + 到该任务为止的累计建议天数。

        1 → 1+3 → 1+3+2，即今天 +1 / +4 / +6 天。
        """
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()

        tasks = sorted(project.tasks, key=lambda item: item.order_index)
        today = date.today()
        assert tasks[0].due_date == today + timedelta(days=1)
        assert tasks[1].due_date == today + timedelta(days=4)
        assert tasks[2].due_date == today + timedelta(days=6)

    def test_stages_linked_and_ordered(self, db: Session) -> None:
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()

        stages = sorted(project.stages, key=lambda item: item.order_index)
        assert [stage.name for stage in stages] == ["阶段一 · 准备", "阶段二 · 产出"]
        # 每个任务都必须挂到阶段上，否则时间线渲染会缺项
        assert all(task.stage_id for task in project.tasks)

    def test_new_tasks_default_to_todo(self, db: Session) -> None:
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()
        assert all(task.status == TaskStatus.TODO for task in project.tasks)

    def test_knowledge_points_and_criteria_persisted(self, db: Session) -> None:
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()

        task_a = next(task for task in project.tasks if task.name == "任务A")
        assert task_a.knowledge_points == ["k1", "k2"]
        assert task_a.deliverable_criteria == "标准A"

    @pytest.mark.parametrize("bad_value", ["abc", None, 0, -5, ""])
    def test_ddl_days_falls_back_to_at_least_one(
        self, db: Session, bad_value: object
    ) -> None:
        """模型的 ddl_days 可能是脏数据，必须回退为正整数，否则 DDL 会错乱。"""
        project = make_project(db)
        persist_decomposition(
            db,
            project,
            [{"name": "阶段", "tasks": [{"name": "脏数据任务", "ddl_days": bad_value}]}],
        )
        db.commit()

        task = project.tasks[0]
        assert task.ddl_days >= 1
        assert task.due_date == date.today() + timedelta(days=task.ddl_days)

    def test_stage_without_name_gets_placeholder(self, db: Session) -> None:
        """缺少名称的阶段不应导致崩溃。"""
        project = make_project(db)
        persist_decomposition(db, project, [{"tasks": [{"name": "任务"}]}])
        db.commit()
        assert project.stages[0].name == "阶段 1"

    def test_tasks_without_name_are_skipped(self, db: Session) -> None:
        project = make_project(db)
        persist_decomposition(
            db,
            project,
            [{"name": "阶段", "tasks": [{"description": "没有名字"}, {"name": "有效任务"}]}],
        )
        db.commit()
        assert [task.name for task in project.tasks] == ["有效任务"]


class TestTaskOrderingIsFree:
    """任务之间**没有**顺序门禁。

    产品的推荐节奏是「完成一个再进入下一个」，但学习者可以按自己的实际情况
    跳着做（例如已经会某部分，想先从后面的任务开始）。因此任意任务都可以直接开始。
    这组用例锁定该行为，防止后续迭代误把门禁加回来。
    """

    def test_last_task_can_start_while_first_is_untouched(self, db: Session) -> None:
        """第一个任务还没开始时，最后一个任务同样可以直接开始。"""
        from app.api.task import _apply_status

        _, tasks = build_tasks(db, [TaskStatus.TODO] * 3)
        _apply_status(tasks[2], TaskStatus.IN_PROGRESS)
        db.commit()

        assert tasks[2].status == TaskStatus.IN_PROGRESS
        assert tasks[0].status == TaskStatus.TODO
        assert tasks[1].status == TaskStatus.TODO

    def test_middle_task_can_start_out_of_order(self, db: Session) -> None:
        from app.api.task import _apply_status

        _, tasks = build_tasks(db, [TaskStatus.TODO] * 3)
        _apply_status(tasks[1], TaskStatus.IN_PROGRESS)
        db.commit()

        assert tasks[1].status == TaskStatus.IN_PROGRESS
        assert tasks[1].started_at is not None

    def test_apply_status_does_not_raise_regardless_of_order(self, db: Session) -> None:
        """_apply_status 不应因前置任务未完成而抛错。"""
        from app.api.task import _apply_status

        _, tasks = build_tasks(
            db, [TaskStatus.TODO, TaskStatus.TODO, TaskStatus.TODO]
        )
        for task in reversed(tasks):
            _apply_status(task, TaskStatus.IN_PROGRESS)
        db.commit()

        assert all(task.status == TaskStatus.IN_PROGRESS for task in tasks)

    def test_task_model_has_no_locking_concept(self) -> None:
        """模型层不再暴露任何锁定语义。"""
        from app.models import Task

        assert not hasattr(Task, "locked")

    def test_schema_omits_locked_field(self) -> None:
        """接口响应不再下发 locked 字段。"""
        from app.schemas.task import TaskOut

        assert "locked" not in TaskOut.model_fields


class TestProgress:
    """整体进度统计。"""

    def test_empty_project_is_not_all_completed(self, db: Session) -> None:
        """0 个任务不能算「全部完成」，否则空项目会直接跳进复盘环节。"""
        project = make_project(db)
        db.commit()

        progress = compute_progress(project)
        assert progress.total == 0
        assert progress.percent == 0
        assert progress.all_completed is False
        assert progress.current_task_id is None

    def test_all_todo(self, db: Session) -> None:
        project, tasks = build_tasks(db, [TaskStatus.TODO] * 3)
        progress = compute_progress(project)

        assert (progress.total, progress.done, progress.in_progress, progress.todo) == (
            3,
            0,
            0,
            3,
        )
        assert progress.percent == 0
        assert progress.current_task_id == tasks[0].id
        assert progress.all_completed is False

    def test_mixed_states(self, db: Session) -> None:
        project, tasks = build_tasks(
            db, [TaskStatus.DONE, TaskStatus.IN_PROGRESS, TaskStatus.TODO]
        )
        progress = compute_progress(project)

        assert (progress.total, progress.done, progress.in_progress, progress.todo) == (
            3,
            1,
            1,
            1,
        )
        assert progress.percent == 33
        # 有进行中的任务时，当前任务应指向它
        assert progress.current_task_id == tasks[1].id

    def test_current_task_falls_back_to_first_todo(self, db: Session) -> None:
        """没有进行中任务时，当前任务指向第一个未开始的任务。"""
        project, tasks = build_tasks(
            db, [TaskStatus.DONE, TaskStatus.TODO, TaskStatus.TODO]
        )
        assert compute_progress(project).current_task_id == tasks[1].id

    def test_all_completed(self, db: Session) -> None:
        project, _ = build_tasks(db, [TaskStatus.DONE] * 3)
        progress = compute_progress(project)

        assert progress.percent == 100
        assert progress.done == 3
        assert progress.todo == 0
        assert progress.all_completed is True

    def test_percent_rounds_down(self, db: Session) -> None:
        """百分比取整（向下），避免 2/3 显示成 67% 却还没做完的错觉。"""
        project = make_project(db)
        persist_decomposition(db, project, DECOMPOSITION)
        db.commit()
        tasks = sorted(project.tasks, key=lambda item: item.order_index)
        tasks[0].status = TaskStatus.DONE
        tasks[1].status = TaskStatus.DONE
        db.commit()

        assert compute_progress(project).percent == 66
