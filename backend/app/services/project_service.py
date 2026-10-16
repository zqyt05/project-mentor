"""项目服务：双路径项目匹配、项目落库与阶段任务拆解。

覆盖 PRD 模块 1（项目智能匹配与生成）与模块 2（项目拆解与 DDL 任务管理）。

双路径路由逻辑：
1. 先用 LLM 判断学习方向属于「技术开发类」还是「通用知识类」
2. 技术类 → 路径 A：GitHub 开源项目检索 + AI 生成推荐理由
3. 通用类 → 路径 B：AI 生成定制实战项目
4. 技术类但检索到的优质项目不足 3 个 → 自动降级到路径 B
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import (
    Project,
    ProjectSource,
    ProjectStatus,
    Stage,
    Task,
    TaskStatus,
    utcnow,
)
from app.schemas.project import (
    ProjectBrief,
    ProjectCandidate,
    ProjectDetail,
    ProjectMatchResponse,
)
from app.schemas.task import ProgressOut
from app.services.github_service import GithubRepo, get_github_service
from app.services.llm_service import get_llm_service, render_prompt
from app.utils.response import CODE_NOT_FOUND, BusinessError

logger = logging.getLogger(__name__)

# ======================================================================
# LLM 输出清洗
# ======================================================================
# 模型偶尔会把字段名当成内容的一部分输出（例如 target_audience 返回
# 「适配人群：零基础也能学」）。界面上字段名由独立标签展示，重复出现会显得冗余，
# 因此在入库前统一剥掉。Prompt 已明确要求不带前缀，这里是兜底。

# 标量字段：需要剥掉的前缀（中英文冒号都考虑）
_SCALAR_LABEL_PREFIXES: dict[str, tuple[str, ...]] = {
    "summary": ("项目简介：", "项目简介:", "推荐理由：", "推荐理由:"),
    "background": ("项目背景：", "项目背景:"),
    "target_audience": ("适配人群：", "适配人群:", "适合人群：", "适合人群:"),
    "pitfalls": (
        "常见学习误区：",
        "常见学习误区:",
        "常见误区：",
        "常见误区:",
        "学习误区：",
        "学习误区:",
    ),
}

# 列表项：剥掉「交付物1：」「实战目标 2、」「目标3，」这类编号前缀。
# 分隔符要覆盖中英文标点 —— 模型用全角逗号「，」的情况很常见。
_LIST_ITEM_PREFIX_RE = re.compile(
    r"^(?:交付物|实战目标|目标|知识点)\s*\d+\s*[：:，,、.。)）\-]\s*"
)


def _clean_scalar(value: Any, key: str) -> str:
    """去掉模型误加的字段名前缀。"""
    text = str(value or "").strip()
    for prefix in _SCALAR_LABEL_PREFIXES.get(key, ()):  # 按声明顺序匹配
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _clean_list_items(values: Any, limit: int) -> list[str]:
    """清理列表字段：去掉编号前缀、丢弃空项、截断到上限。"""
    cleaned: list[str] = []
    for item in values or []:
        text = _LIST_ITEM_PREFIX_RE.sub("", str(item).strip()).strip()
        if text:
            cleaned.append(text)
    return cleaned[:limit]

# 路径 A 最终输出的项目数量
_GITHUB_RESULT_LIMIT = 5
# 路径 B 生成的定制项目数量
_CUSTOM_RESULT_COUNT = 3


# ======================================================================
# 领域判断与路由
# ======================================================================


async def classify_domain(domain: str) -> dict[str, Any]:
    """调用 LLM 判断学习方向类型，并产出 GitHub 检索所需的关键词与语言。

    返回：{category, reason, search_keywords, language, custom_hint}
    """
    llm = get_llm_service()
    payload = await llm.acomplete_json(
        system_prompt="你是一个严谨的学习方向分析器，只输出 JSON。",
        user_prompt=render_prompt("domain_route", domain=domain),
    )
    if not isinstance(payload, dict):
        raise BusinessError("领域判断结果格式异常，请重试")

    category = str(payload.get("category", "general")).strip().lower()
    if category not in ("technical", "general"):
        category = "general"

    return {
        "category": category,
        "reason": str(payload.get("reason", "") or ""),
        "search_keywords": str(payload.get("search_keywords", "") or "").strip(),
        "language": str(payload.get("language", "") or "").strip() or None,
        "custom_hint": str(payload.get("custom_hint", "") or ""),
    }


# ======================================================================
# 路径 A：GitHub 开源项目检索 + AI 推荐
# ======================================================================


def _candidate_from_repo(repo: GithubRepo, generated: dict[str, Any], difficulty: str) -> ProjectCandidate:
    """把 GitHub 仓库 + LLM 生成的推荐信息合并为一张项目卡片。"""
    return ProjectCandidate(
        name=repo.name,
        source=ProjectSource.GITHUB,
        difficulty=difficulty,
        summary=_clean_scalar(generated.get("summary") or repo.description, "summary"),
        background=_clean_scalar(generated.get("background") or repo.description, "background"),
        goals=_clean_list_items(generated.get("goals"), 4),
        core_points=_clean_list_items(generated.get("core_points"), 5),
        deliverables=_clean_list_items(generated.get("deliverables"), 4),
        target_audience=_clean_scalar(generated.get("target_audience"), "target_audience"),
        pitfalls=_clean_scalar(generated.get("pitfalls"), "pitfalls"),
        match_reason=(f"Star {repo.stars} · {repo.language or '未标注语言'}"),
        repo_url=repo.url,
        repo_full_name=repo.full_name,
        stars=repo.stars,
        language=repo.language,
    )


async def match_github_projects(
    domain: str, difficulty: str, keywords: str, language: str | None
) -> list[ProjectCandidate]:
    """路径 A：检索 GitHub 优质项目，并按难度匹配度排序输出 Top N。"""
    github = get_github_service()

    # 有关键词时优先按关键词+语言检索；结果不足时放宽语言限制再试一次
    repos = await github.search(keywords, language=language)
    if len(repos) < _GITHUB_RESULT_LIMIT and language:
        logger.info("语言限定下候选不足，放宽语言限制重试：%s", keywords)
        fallback_repos = await github.search(keywords, language=None)
        seen = {repo.full_name for repo in repos}
        repos.extend(repo for repo in fallback_repos if repo.full_name not in seen)

    # 通用技术方向（如「算法」）关键词可能检索不到，退回用方向原文再试
    if not repos:
        logger.info("关键词检索无结果，使用方向原文重试：%s", domain)
        repos = await github.search(domain, language=None)

    # 注意：这里不再因为「少于 3 个」就直接放弃。
    # 检索到几个就先给几个，数量不足的部分由调用方用 AI 定制项目补齐，
    # 避免明明有 1-2 个高度相关的优质开源项目，却全部丢掉换成定制项目。
    if not repos:
        logger.info("未检索到符合筛选条件的开源项目：%s", keywords)
        return []

    repo_pool = repos[: settings.GITHUB_CANDIDATE_LIMIT]
    llm = get_llm_service()
    payload = await llm.acomplete_json(
        system_prompt="你是资深技术导师，擅长评估开源项目对学习者的适配度，只输出 JSON。",
        user_prompt=render_prompt(
            "github_recommend",
            domain=domain,
            difficulty=difficulty,
            candidates=github.render_candidates(repo_pool),
        ),
    )

    evaluated = payload.get("projects", []) if isinstance(payload, dict) else []
    # 按 index 建立索引，保证与候选仓库一一对应
    by_index: dict[int, dict[str, Any]] = {}
    for item in evaluated:
        if isinstance(item, dict):
            try:
                by_index[int(item.get("index", -1))] = item
            except (TypeError, ValueError):
                continue

    # 组装 (适配度, star 数, 项目卡片)，随后按「难度匹配度优先、star 数次之」排序
    scored: list[tuple[int, int, ProjectCandidate]] = []
    for index, repo in enumerate(repo_pool):
        generated = by_index.get(index, {})
        try:
            fit_value = int(generated.get("fit", 0))
        except (TypeError, ValueError):
            fit_value = 0
        scored.append(
            (fit_value, repo.stars, _candidate_from_repo(repo, generated, difficulty))
        )

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [candidate for _fit, _stars, candidate in scored[:_GITHUB_RESULT_LIMIT]]


# ======================================================================
# 路径 B：AI 定制实战项目生成
# ======================================================================


async def generate_custom_projects(
    domain: str, difficulty: str, count: int = _CUSTOM_RESULT_COUNT
) -> list[ProjectCandidate]:
    """路径 B：调用 LLM 生成定制化实战项目。

    :param count: 需要生成的项目数量。技术类方向若 GitHub 优质项目不足时，
                  会用本函数补齐差额，因此数量是可变的。
    """
    count = max(1, min(count, _CUSTOM_RESULT_COUNT))
    llm = get_llm_service()
    payload = await llm.acomplete_json(
        system_prompt="你是实战派学习导师，擅长设计小而实的实战项目，只输出 JSON。",
        user_prompt=render_prompt(
            "custom_project", domain=domain, difficulty=difficulty, count=str(count)
        ),
    )

    raw_projects = payload.get("projects", []) if isinstance(payload, dict) else []
    candidates: list[ProjectCandidate] = []
    for item in raw_projects:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        candidates.append(
            ProjectCandidate(
                name=str(item.get("name")),
                source=ProjectSource.CUSTOM,
                difficulty=str(item.get("difficulty") or difficulty),
                summary=_clean_scalar(item.get("summary"), "summary"),
                background=_clean_scalar(item.get("background"), "background"),
                goals=_clean_list_items(item.get("goals"), 4),
                core_points=_clean_list_items(item.get("core_points"), 5),
                deliverables=_clean_list_items(item.get("deliverables"), 4),
                target_audience=_clean_scalar(item.get("target_audience"), "target_audience"),
                pitfalls=_clean_scalar(item.get("pitfalls"), "pitfalls"),
                match_reason="AI 定制项目 · 交付物导向",
            )
        )

    if not candidates:
        raise BusinessError("AI 未能生成有效项目，请调整学习方向描述后重试")

    return candidates[:count]


# ======================================================================
# 对外主入口：项目匹配
# ======================================================================


async def match_projects(domain: str, difficulty: str) -> ProjectMatchResponse:
    """项目智能匹配主流程：领域判断 → 双路径路由 → 输出候选项目卡片。"""
    route = await classify_domain(domain)

    if route["category"] == "technical":
        keywords = route["search_keywords"] or domain
        github_candidates = await match_github_projects(
            domain, difficulty, keywords, route["language"]
        )

        # GitHub 优质项目不足时，用 AI 定制项目补齐差额，而不是整体丢弃。
        # 这样即使只找到 1-2 个高度相关的开源项目，也仍然会呈现给用户。
        shortage = settings.GITHUB_MIN_QUALIFIED - len(github_candidates)
        if shortage <= 0:
            return ProjectMatchResponse(
                path=ProjectSource.GITHUB,
                route_reason=(
                    f"「{domain}」属于技术开发类（{route['reason']}），"
                    f"已为你检索到 {len(github_candidates)} 个优质开源实战项目"
                ),
                projects=github_candidates,
            )

        custom = await generate_custom_projects(domain, difficulty, count=shortage)

        if github_candidates:
            return ProjectMatchResponse(
                path=ProjectSource.GITHUB,
                route_reason=(
                    f"「{domain}」属于技术开发类（{route['reason']}）。"
                    f"GitHub 上符合「Star > 500、近一年有更新、README 完整」的优质开源项目"
                    f"只有 {len(github_candidates)} 个，不足 {settings.GITHUB_MIN_QUALIFIED} 个，"
                    f"已用 {len(custom)} 个 AI 定制实战项目补齐差额"
                ),
                projects=github_candidates + custom,
            )

        return ProjectMatchResponse(
            path=ProjectSource.CUSTOM,
            route_reason=(
                f"「{domain}」属于技术开发类，但 GitHub 上符合"
                f"「Star > 500、近一年有更新、README 完整」的优质开源项目为 0 个，"
                f"已改为全部由 AI 定制实战项目"
            ),
            projects=custom,
        )

    custom = await generate_custom_projects(domain, difficulty)
    hint = route.get("custom_hint") or ""
    return ProjectMatchResponse(
        path=ProjectSource.CUSTOM,
        route_reason=(
            f"「{domain}」属于通用知识类（{route['reason']}），"
            f"已为你定制 {len(custom)} 个交付物明确的实战项目"
            + (f"。{hint}" if hint else "")
        ),
        projects=custom,
    )


# ======================================================================
# 项目拆解
# ======================================================================


def _build_project_info(project: Project) -> str:
    """把项目信息渲染为 Prompt 片段，供拆解与答疑复用。"""
    lines = [
        f"- 项目名称：{project.name}",
        f"- 项目来源：{'GitHub 开源项目' if project.source == ProjectSource.GITHUB else 'AI 定制项目'}",
        f"- 学习方向：{project.domain}",
        f"- 难度：{project.difficulty}",
        f"- 项目简介：{project.summary or '（无）'}",
    ]
    if project.background:
        lines.append(f"- 项目背景：{project.background}")
    if project.goals:
        lines.append(f"- 实战目标：{'；'.join(str(goal) for goal in project.goals)}")
    if project.core_points:
        lines.append(f"- 核心知识点：{'、'.join(str(point) for point in project.core_points)}")
    if project.deliverables:
        lines.append(f"- 最终交付物：{'；'.join(str(d) for d in project.deliverables)}")
    if project.repo_url:
        lines.append(f"- 开源仓库：{project.repo_url}（Star {project.stars or 0}）")
    if project.readme_digest:
        # 附上真实 README 内容，让拆解与答疑基于项目实况而不是仅凭仓库名猜测
        lines.append(f"- README 摘要：\n{project.readme_digest}")
    return "\n".join(lines)


async def decompose_project(project: Project) -> list[dict[str, Any]]:
    """调用 LLM 把项目拆解为阶段化任务。"""
    llm = get_llm_service()
    payload = await llm.acomplete_json(
        system_prompt="你是企业导师，擅长把项目拆解为带 DDL 的可执行阶段任务，只输出 JSON。",
        user_prompt=render_prompt(
            "task_decompose",
            project_info=_build_project_info(project),
            domain=project.domain,
            difficulty=project.difficulty,
        ),
    )

    stages = payload.get("stages", []) if isinstance(payload, dict) else []
    if not stages:
        raise BusinessError("AI 未能生成任务拆解结果，请重试")
    return stages


def persist_decomposition(db: Session, project: Project, stages: list[dict[str, Any]]) -> None:
    """把 LLM 返回的阶段任务写入数据库，并按顺序计算每个任务的 DDL 日期。

    DDL 计算规则：从今天起按任务先后顺序累加各自的建议天数，
    即每个任务的截止日 = 项目开始日 + 其之前所有任务（含自身）的建议天数之和。
    """
    today = date.today()
    offset_days = 0
    task_order = 0

    for stage_index, raw_stage in enumerate(stages):
        if not isinstance(raw_stage, dict):
            continue
        stage = Stage(
            project_id=project.id,
            order_index=stage_index,
            name=str(raw_stage.get("name") or f"阶段 {stage_index + 1}"),
            description=str(raw_stage.get("description", "") or ""),
            is_milestone=bool(raw_stage.get("is_milestone", True)),
        )
        db.add(stage)
        db.flush()  # 取得 stage.id，供任务外键引用

        for raw_task in raw_stage.get("tasks") or []:
            if not isinstance(raw_task, dict) or not raw_task.get("name"):
                continue
            try:
                ddl_days = max(1, int(raw_task.get("ddl_days") or 1))
            except (TypeError, ValueError):
                ddl_days = 1

            offset_days += ddl_days
            db.add(
                Task(
                    project_id=project.id,
                    stage_id=stage.id,
                    order_index=task_order,
                    name=str(raw_task.get("name")),
                    description=str(raw_task.get("description", "") or ""),
                    knowledge_points=[
                        str(point) for point in (raw_task.get("knowledge_points") or [])
                    ],
                    deliverable_criteria=str(raw_task.get("deliverable_criteria", "") or ""),
                    ddl_days=ddl_days,
                    due_date=today + timedelta(days=offset_days),
                    status=TaskStatus.TODO,
                )
            )
            task_order += 1

    project.updated_at = utcnow()
    db.flush()


async def start_project(
    db: Session,
    domain: str,
    difficulty: str,
    candidate: ProjectCandidate,
    visitor_id: str | None = None,
) -> Project:
    """用户点击「开始学习」：落库项目并完成阶段任务初始化。"""
    project = Project(
        name=candidate.name,
        source=candidate.source,
        domain=domain,
        difficulty=difficulty or candidate.difficulty,
        status=ProjectStatus.LEARNING,
        # 归属当前访客；门禁关闭时为 None（本机所有者）
        owner_id=visitor_id,
        summary=candidate.summary,
        background=candidate.background,
        goals=candidate.goals,
        core_points=candidate.core_points,
        deliverables=candidate.deliverables,
        target_audience=candidate.target_audience,
        pitfalls=candidate.pitfalls,
        repo_url=candidate.repo_url,
        repo_full_name=candidate.repo_full_name,
        stars=candidate.stars,
        language=candidate.language,
    )
    db.add(project)
    db.flush()  # 取得 project.id

    # GitHub 项目：拉取真实 README 摘要，作为答疑与复盘的事实依据。
    # 单独存字段（而不是拼进 background），前端可以折叠展示并回链仓库地址。
    if candidate.source == ProjectSource.GITHUB and candidate.repo_full_name:
        project.readme_digest = await fetch_readme_digest(candidate.repo_full_name)

    stages = await decompose_project(project)
    persist_decomposition(db, project, stages)
    db.commit()
    db.refresh(project)
    return project


async def fetch_readme_digest(full_name: str, max_chars: int = 2000) -> str:
    """拉取 GitHub 仓库 README 的头部内容，失败时静默返回空串。"""
    try:
        github = get_github_service()
        client = await github._get_client()  # noqa: SLF001 - 复用同一连接池
        response = await client.get(
            f"/repos/{full_name}/readme",
            headers={"Accept": "application/vnd.github.raw"},
        )
        if response.status_code == 200:
            text = (response.text or "").strip()
            return text[:max_chars]
    except Exception:  # noqa: BLE001 - README 属于增强信息，失败不影响主流程
        logger.warning("拉取 README 摘要失败：%s", full_name)
    return ""


# ======================================================================
# 查询与进度
# ======================================================================


def compute_progress(project: Project) -> ProgressOut:
    """计算项目整体进度与当前进行中的任务。"""
    tasks = project.tasks
    total = len(tasks)
    done = sum(1 for task in tasks if task.status == TaskStatus.DONE)
    in_progress = sum(1 for task in tasks if task.status == TaskStatus.IN_PROGRESS)
    todo = total - done - in_progress

    current = next((task for task in tasks if task.status == TaskStatus.IN_PROGRESS), None)
    if current is None:
        current = next((task for task in tasks if task.status == TaskStatus.TODO), None)

    return ProgressOut(
        total=total,
        done=done,
        in_progress=in_progress,
        todo=todo,
        percent=int(done / total * 100) if total else 0,
        current_task_id=current.id if current else None,
        all_completed=bool(total) and done == total,
    )


def get_project(db: Session, project_id: int, visitor_id: str | None = None) -> Project:
    """按 ID 读取项目（含阶段与任务），不存在则报错。

    这是读取项目的**唯一入口**，因此把访客归属校验放在这里收口 ——
    所有项目级/任务级接口最终都会走到这个函数，不必逐个补检查。

    `visitor_id` 为 None 表示门禁关闭（本地单用户模式），此时不做归属过滤。

    归属不符时返回 **404 而不是 403**：403 等于告诉对方「这个 id 存在但你没权限」，
    会泄露项目的存在性；404 让越权访问与「不存在」不可区分。
    """
    project = db.get(Project, project_id)
    if project is None:
        raise BusinessError(f"项目不存在（id={project_id}）", CODE_NOT_FOUND)
    if visitor_id is not None and project.owner_id != visitor_id:
        # 刻意使用与「不存在」完全相同的提示，避免泄露存在性
        raise BusinessError(f"项目不存在（id={project_id}）", CODE_NOT_FOUND)
    return project


def get_project_detail(
    db: Session, project_id: int, visitor_id: str | None = None
) -> ProjectDetail:
    """读取项目详情并附带进度信息。"""
    project = get_project(db, project_id, visitor_id)
    detail = ProjectDetail.model_validate(project)
    detail.progress = compute_progress(project)
    # 按阶段顺序与任务顺序稳定输出
    detail.stages.sort(key=lambda stage: stage.order_index)
    for stage in detail.stages:
        stage.tasks.sort(key=lambda task: task.order_index)
    detail.tasks = sorted(detail.tasks, key=lambda task: task.order_index)
    return detail


def list_projects(
    db: Session, limit: int = 100, visitor_id: str | None = None
) -> list[ProjectBrief]:
    """查看历史学习项目列表（按更新时间倒序）。

    `visitor_id` 非 None 时只返回该访客自己的项目（演示模式的隔离）。
    """
    stmt = (
        select(Project)
        .options(selectinload(Project.tasks), selectinload(Project.stages))
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    if visitor_id is not None:
        stmt = stmt.where(Project.owner_id == visitor_id)
    projects = db.execute(stmt).scalars().all()
    briefs: list[ProjectBrief] = []
    for project in projects:
        brief = ProjectBrief.model_validate(project)
        brief.progress = compute_progress(project)
        briefs.append(brief)
    return briefs


def refresh_project_status(db: Session, project: Project) -> None:
    """根据任务完成情况同步项目状态（全部完成则进入复盘环节）。"""
    progress = compute_progress(project)
    if progress.all_completed and project.status == ProjectStatus.LEARNING:
        project.status = ProjectStatus.REVIEWING
    elif not progress.all_completed and project.status == ProjectStatus.REVIEWING:
        # 用户取消勾选任务时回退到学习状态
        project.status = ProjectStatus.LEARNING
    project.updated_at = utcnow()
    db.commit()


def count_projects(db: Session) -> int:
    """统计项目总数（供首页/健康检查使用）。"""
    return db.execute(select(func.count(Project.id))).scalar_one()


__all__ = [
    "classify_domain",
    "match_projects",
    "match_github_projects",
    "generate_custom_projects",
    "start_project",
    "decompose_project",
    "persist_decomposition",
    "compute_progress",
    "get_project",
    "get_project_detail",
    "list_projects",
    "refresh_project_status",
    "build_project_context",
    "fetch_readme_digest",
]


def build_project_context(project: Project, task: Task | None = None) -> str:
    """构建答疑 / 复盘用的完整项目上下文。

    上下文 = 项目基本信息 + 当前阶段任务 + 项目阶段总览。
    这是「场景化精准答疑」的关键：把模型锚定在具体任务上。
    """
    lines = ["【项目信息】", _build_project_info(project)]

    if task is not None:
        stage = task.stage
        lines += [
            "",
            "【学习者当前正在做的任务】",
            f"- 所属阶段：{stage.name if stage else '未分阶段'}",
            f"- 任务名称：{task.name}",
            f"- 任务描述：{task.description or '（无）'}",
            f"- 需掌握知识点：{'、'.join(task.knowledge_points) if task.knowledge_points else '（无）'}",
            f"- 交付标准：{task.deliverable_criteria or '（无）'}",
            f"- 任务状态：{'已完成' if task.status == TaskStatus.DONE else '进行中' if task.status == TaskStatus.IN_PROGRESS else '未开始'}",
            f"- DDL：{task.due_date.isoformat() if task.due_date else '未设置'}",
        ]

        # 附带项目阶段总览，让导师知道学习者处在整个项目的哪个位置
        if project.tasks:
            lines += ["", "【项目任务总览（★ 为当前任务）】"]
            for item in project.tasks:
                marker = "★" if item.id == task.id else " "
                status_label = {
                    TaskStatus.DONE: "已完成",
                    TaskStatus.IN_PROGRESS: "进行中",
                    TaskStatus.TODO: "未开始",
                }.get(item.status, item.status)
                lines.append(f" {marker} [{status_label}] {item.name}")
    else:
        progress = compute_progress(project)
        lines += [
            "",
            "【项目整体进度】",
            f"- 共 {progress.total} 个任务，已完成 {progress.done} 个，"
            f"进行中 {progress.in_progress} 个，未开始 {progress.todo} 个",
        ]

    return "\n".join(lines)
