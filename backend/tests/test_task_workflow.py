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


class TestTaskLocking:
    """顺序门禁：完成前一个任务才解锁下一个。"""

    def test_only_first_task_unlocked_initially(self, db: Session) -> None:
        _, tasks = build_tasks(
            db, [TaskStatus.TODO, TaskStatus.TODO, TaskStatus.TODO]
        )
        assert tasks[0].locked is False
        assert tasks[1].locked is True
        assert tasks[2].locked is True

    def test_completing_previous_unlocks_next(self, db: Session) -> None:
        _, tasks = build_tasks(
            db, [TaskStatus.DONE, TaskStatus.TODO, TaskStatus.TODO]
        )
        assert tasks[1].locked is False
        # 第二个还没完成，所以第三个仍然锁着
        assert tasks[2].locked is True

    def test_locked_requires_all_previous_done(self, db: Session) -> None:
        """前序任务里只要有一个没完成，当前任务就不算解锁。"""
        _, tasks = build_tasks(
            db, [TaskStatus.DONE, TaskStatus.IN_PROGRESS, TaskStatus.TODO]
        )
        assert tasks[2].locked is True

    def test_done_and_in_progress_are_never_locked(self, db: Session) -> None:
        """已完成 / 进行中的任务永不锁定，避免用户回退状态时死锁。"""
        _, tasks = build_tasks(
            db, [TaskStatus.TODO, TaskStatus.DONE, TaskStatus.IN_PROGRESS]
        )
        assert tasks[1].locked is False
        assert tasks[2].locked is False

    def test_nothing_locked_when_all_done(self, db: Session) -> None:
        _, tasks = build_tasks(db, [TaskStatus.DONE] * 3)
        assert not any(task.locked for task in tasks)


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
