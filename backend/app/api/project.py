"""项目匹配与生成接口（PRD 模块 1）。

路径前缀：/api/project
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import current_visitor
from app.schemas.project import (
    ProjectBrief,
    ProjectDetail,
    ProjectMatchRequest,
    ProjectStartRequest,
)
from app.services import project_service
from app.utils.response import success

router = APIRouter(prefix="/api/project", tags=["项目匹配与生成"])


@router.post("/match", summary="双路径项目智能匹配")
async def match_projects(
    payload: ProjectMatchRequest,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """输入学习方向 + 难度，返回项目卡片列表。

    - 技术类方向 → GitHub 开源项目检索（路径 A）
    - 通用类方向 / 检索不足 → AI 定制实战项目（路径 B）
    """
    result = await project_service.match_projects(
        payload.domain, payload.difficulty, db
    )
    return success(result.model_dump(), message="项目匹配完成")


@router.post("/start", summary="开始学习（项目落库 + 任务拆解）")
async def start_project(
    payload: ProjectStartRequest,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """用户点击「开始学习」：初始化项目并拆解为阶段任务与 DDL。"""
    project = await project_service.start_project(
        db,
        payload.domain,
        payload.difficulty,
        payload.project,
        visitor_id=visitor,
    )
    # 归属校验：新项目必然属于当前访客，这里传 visitor 是保持一致性
    detail = project_service.get_project_detail(db, project.id, visitor)
    return success(detail.model_dump(), message="项目已初始化，开始学习吧")


@router.get("/list", summary="历史学习项目列表")
def list_projects(
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """查看历史学习项目列表（PRD 模块 5 · 数据持久化）。"""
    projects: list[ProjectBrief] = project_service.list_projects(db, visitor_id=visitor)
    return success([project.model_dump() for project in projects])


@router.get("/{project_id}", summary="项目详情（含阶段任务时间线）")
def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """获取项目总览页所需的全部数据。"""
    detail: ProjectDetail = project_service.get_project_detail(db, project_id, visitor)
    return success(detail.model_dump())


@router.delete("/{project_id}", summary="删除项目及其全部学习数据")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """删除项目（级联删除任务、对话、复盘）。MVP 仅提供删除，不做归档。"""
    project = project_service.get_project(db, project_id, visitor)
    db.delete(project)
    db.commit()
    return success({"id": project_id}, message="项目已删除")
