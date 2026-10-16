"""费曼复盘接口（PRD 模块 4）。

路径前缀：/api/review
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import current_visitor
from app.schemas.review import ReviewGenerateRequest, ReviewOut
from app.services import review_service
from app.utils.response import success

router = APIRouter(prefix="/api/review", tags=["费曼复盘"])


@router.get("/guide", summary="获取复盘引导（3 种形式 + 引导问题）")
def get_guide() -> dict:
    """复盘页初始化时调用，返回可选形式与引导性问题。"""
    return success(review_service.get_guide())


@router.post("/generate", summary="提交复盘内容，AI 纠错补全并生成最终文档")
async def generate(
    payload: ReviewGenerateRequest,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """用户提交自己的复盘内容 → AI 从纠错/补全/结构/深化四个维度处理。"""
    review = await review_service.generate_review(
        db,
        payload.project_id,
        payload.form,
        payload.user_content,
        visitor_id=visitor,
    )
    return success(ReviewOut.model_validate(review).model_dump(), message="复盘文档已生成")


@router.get("/{project_id}", summary="获取项目最新复盘内容")
def get_review(
    project_id: int,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """读取最近一次复盘；尚未复盘时返回 data=null，由前端展示引导区。"""
    review = review_service.get_latest_review(db, project_id, visitor)
    return success(ReviewOut.model_validate(review).model_dump() if review else None)
