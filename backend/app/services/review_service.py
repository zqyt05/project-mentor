"""费曼复盘服务。

对应 PRD 模块 4：所有任务完成后进入复盘环节。
用户先用自己的话输出，AI 再从「纠错 / 补全 / 结构优化 / 深化建议」四个维度处理，
最终生成可一键复制的复盘文档。
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, ProjectStatus, Review, ReviewForm, utcnow
from app.services.llm_service import get_llm_service, render_prompt
from app.services.project_service import build_project_context, get_project
from app.utils.response import CODE_NOT_FOUND, BusinessError

logger = logging.getLogger(__name__)

# 三种复盘形式（对应 PRD「提供 3 种复盘形式选项」）
REVIEW_FORMS: list[dict[str, str]] = [
    {
        "value": ReviewForm.STRUCTURED,
        "label": "结构化技术总结文档",
        "description": "按「背景 → 方案 → 实现 → 问题 → 结论」组织，适合沉淀为个人知识库",
    },
    {
        "value": ReviewForm.BLOG,
        "label": "项目复盘博客",
        "description": "面向读者的叙事型复盘，适合发布到掘金 / 知乎 / 个人博客",
    },
    {
        "value": ReviewForm.INTERVIEW,
        "label": "面试口述提纲",
        "description": "按面试官提问逻辑组织，适合作为项目经历的讲述脚本",
    },
]

_FORM_LABELS = {item["value"]: item["label"] for item in REVIEW_FORMS}

# 引导性问题（对应 PRD 模块 4）
REVIEW_QUESTIONS: list[str] = [
    "用通俗的话讲清楚：这个项目是做什么的？整体逻辑是怎样的？",
    "项目中最难的部分是什么？你是怎么攻克它的？",
    "完成过程中踩过哪些坑？有什么经验教训？",
    "这个项目用到了哪些核心知识 / 方法？它们分别解决了什么问题？",
]


def get_guide() -> dict:
    """返回复盘引导信息（形式选项 + 引导问题）。"""
    return {"forms": REVIEW_FORMS, "questions": REVIEW_QUESTIONS}


def get_latest_review(
    db: Session, project_id: int, visitor_id: str | None = None
) -> Review | None:
    """读取项目最近一次复盘记录。"""
    # 先校验归属，避免越权读取他人的复盘内容
    get_project(db, project_id, visitor_id)
    stmt = (
        select(Review)
        .where(Review.project_id == project_id)
        .order_by(Review.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def get_review_or_404(
    db: Session, project_id: int, visitor_id: str | None = None
) -> Review:
    """读取复盘记录，不存在时给出友好提示。"""
    review = get_latest_review(db, project_id, visitor_id)
    if review is None:
        raise BusinessError("该项目还没有复盘记录，请先提交复盘内容", CODE_NOT_FOUND)
    return review


async def generate_review(
    db: Session,
    project_id: int,
    form: str,
    user_content: str,
    visitor_id: str | None = None,
) -> Review:
    """提交用户复盘内容，调用 LLM 纠错补全并生成最终文档。"""
    project = get_project(db, project_id, visitor_id)
    user_content = user_content.strip()
    if not user_content:
        raise BusinessError("复盘内容不能为空")

    form_label = _FORM_LABELS.get(form, REVIEW_FORMS[0]["label"])

    llm = get_llm_service()
    payload = await llm.acomplete_json(
        system_prompt="你是严格但耐心的导师，擅长用费曼学习法检验学习者的理解，只输出 JSON。",
        user_prompt=render_prompt(
            "feynman_review",
            project_info=build_project_context(project, task=None),
            form_label=form_label,
            user_content=user_content,
        ),
        max_tokens=16384,  # 最终文档较长，单独放大 token 预算
    db=db,
    )

    if not isinstance(payload, dict):
        raise BusinessError("AI 复盘结果格式异常，请重试")

    final_document = str(payload.get("final_document", "") or "").strip()
    if not final_document:
        # 兜底：模型偶尔只给分项结果，没有拼装最终文档
        logger.warning("AI 未返回 final_document，使用分项结果兜底拼装")
        final_document = _fallback_document(
            project, form_label, user_content, payload
        )

    # 始终只保留最新一次复盘，避免历史堆积造成前端歧义
    for old in db.execute(
        select(Review).where(Review.project_id == project.id)
    ).scalars().all():
        db.delete(old)
    db.flush()

    review = Review(
        project_id=project.id,
        form=form,
        user_content=user_content,
        final_content=final_document,
        corrections=[str(item) for item in (payload.get("corrections") or [])],
        supplements=[str(item) for item in (payload.get("supplements") or [])],
        structure_advice=str(payload.get("structure_advice", "") or ""),
        next_steps=[str(item) for item in (payload.get("next_steps") or [])],
    )

    db.add(review)
    project.status = ProjectStatus.COMPLETED
    project.updated_at = utcnow()
    db.commit()
    db.refresh(review)
    return review


def _fallback_document(
    project: Project, form_label: str, user_content: str, payload: dict
) -> str:
    """当模型未返回完整文档时，用分项结果拼装一份可用的复盘文档。"""
    sections = [
        f"# {project.name} · {form_label}",
        "",
        "## 一、我的复盘",
        "",
        user_content,
    ]
    corrections = payload.get("corrections") or []
    if corrections:
        sections += ["", "## 二、理解纠错", ""]
        sections += [f"- {item}" for item in corrections]

    supplements = payload.get("supplements") or []
    if supplements:
        sections += ["", "## 三、知识点补全", ""]
        sections += [f"- {item}" for item in supplements]

    if payload.get("structure_advice"):
        sections += ["", "## 四、结构优化建议", "", str(payload["structure_advice"])]

    next_steps = payload.get("next_steps") or []
    if next_steps:
        sections += ["", "## 五、下一步深化学习", ""]
        sections += [f"- {item}" for item in next_steps]

    return "\n".join(sections)


__all__ = [
    "REVIEW_FORMS",
    "REVIEW_QUESTIONS",
    "generate_review",
    "get_guide",
    "get_latest_review",
    "get_review_or_404",
]
