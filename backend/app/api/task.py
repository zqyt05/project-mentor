"""任务管理接口（PRD 模块 2）。

路径前缀：/api/task
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, TaskStatus, utcnow
from app.schemas.task import ProgressOut, StageOut, TaskOut, TaskUpdateRequest
from app.services import project_service
from app.utils.response import CODE_NOT_FOUND, BusinessError, success

router = APIRouter(prefix="/api/task", tags=["任务与 DDL 管理"])


def _get_task(db: Session, task_id: int) -> Task:
    """读取任务，不存在则报错。"""
    task = db.get(Task, task_id)
    if task is None:
        raise BusinessError(f"任务不存在（id={task_id}）", CODE_NOT_FOUND)
    return task


def _serialize(task: Task) -> dict:
    return TaskOut.model_validate(task).model_dump()


@router.get("/project/{project_id}/stages", summary="获取项目的阶段任务时间线")
def list_stages(project_id: int, db: Session = Depends(get_db)) -> dict:
    """按阶段顺序返回任务列表，供左侧主窗口的任务列表页使用。"""
    project = project_service.get_project(db, project_id)
    stages = sorted(project.stages, key=lambda stage: stage.order_index)
    payload = []
    for stage in stages:
        item = StageOut.model_validate(stage)
        item.tasks.sort(key=lambda task: task.order_index)
        payload.append(item.model_dump())
    return success(payload)


@router.get("/project/{project_id}/progress", summary="获取项目整体进度")
def get_progress(project_id: int, db: Session = Depends(get_db)) -> dict:
    """返回整体进度条所需的统计数据。"""
    project = project_service.get_project(db, project_id)
    progress: ProgressOut = project_service.compute_progress(project)
    return success(progress.model_dump())


@router.get("/{task_id}", summary="获取任务详情")
def get_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    return success(_serialize(_get_task(db, task_id)))


@router.patch("/{task_id}", summary="更新任务（DDL / 状态 / 内容）")
def update_task(
    task_id: int, payload: TaskUpdateRequest, db: Session = Depends(get_db)
) -> dict:
    """支持用户手动调整 DDL 日期、任务状态与描述内容。"""
    task = _get_task(db, task_id)

    if payload.name is not None:
        task.name = payload.name.strip() or task.name
    if payload.description is not None:
        task.description = payload.description
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.knowledge_points is not None:
        task.knowledge_points = payload.knowledge_points
    if payload.deliverable_criteria is not None:
        task.deliverable_criteria = payload.deliverable_criteria

    if payload.status is not None:
        _apply_status(task, payload.status)

    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)

    project = project_service.get_project(db, task.project_id)
    project_service.refresh_project_status(db, project)
    return success(_serialize(task), message="任务已更新")


def _apply_status(task: Task, status: str) -> None:
    """统一处理状态迁移时的时间戳与门禁校验。"""
    if status == TaskStatus.IN_PROGRESS:
        if task.locked:
            raise BusinessError("请先完成前面的任务，再开始当前任务")
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = task.started_at or utcnow()
    elif status == TaskStatus.DONE:
        task.status = TaskStatus.DONE
        task.completed_at = utcnow()
    elif status == TaskStatus.TODO:
        # 回退到未开始：清空时间戳，保持数据一致
        task.status = TaskStatus.TODO
        task.started_at = None
        task.completed_at = None


@router.post("/{task_id}/start", summary="开始当前任务")
def start_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """任务状态变为「进行中」，返回更新后的任务与项目进度。

    右侧答疑窗口会随之把上下文切换为该任务。
    """
    task = _get_task(db, task_id)
    _apply_status(task, TaskStatus.IN_PROGRESS)
    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)

    project = project_service.get_project(db, task.project_id)
    progress = project_service.compute_progress(project)
    return success(
        {"task": _serialize(task), "progress": progress.model_dump()},
        message="任务已开始，右侧答疑窗口已切换到该任务上下文",
    )


@router.post("/{task_id}/complete", summary="标记任务完成")
def complete_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """标记任务完成并自动解锁下一个任务；全部完成时项目进入复盘环节。"""
    task = _get_task(db, task_id)
    _apply_status(task, TaskStatus.DONE)
    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)

    project = project_service.get_project(db, task.project_id)
    project_service.refresh_project_status(db, project)
    db.refresh(project)

    progress = project_service.compute_progress(project)
    unlocked = next(
        (
            item
            for item in sorted(project.tasks, key=lambda x: x.order_index)
            if item.status == TaskStatus.TODO and not item.locked
        ),
        None,
    )
    return success(
        {
            "task": _serialize(task),
            "progress": progress.model_dump(),
            "project_status": project.status,
            "unlocked_task": _serialize(unlocked) if unlocked else None,
        },
        message=(
            "全部任务已完成，进入费曼复盘环节"
            if progress.all_completed
            else "任务已完成，已解锁下一个任务"
        ),
    )


@router.post("/{task_id}/reset", summary="重置任务为未开始")
def reset_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """把任务退回「未开始」（用户误点完成时使用）。"""
    task = _get_task(db, task_id)
    _apply_status(task, TaskStatus.TODO)
    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)

    project = project_service.get_project(db, task.project_id)
    project_service.refresh_project_status(db, project)
    return success(_serialize(task), message="任务已重置为未开始")
