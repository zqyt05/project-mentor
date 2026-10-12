"""GitHub 服务：调用 GitHub REST API v3 检索优质开源项目。

筛选条件（对应 PRD 模块 1 · 路径 A）：
- stars > 500
- 近一年内有更新（pushed 时间）
- 有较完整的 README
- 语言匹配（可选）

按 stars 倒序取 Top N 候选，交给 LLM 生成推荐理由。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx

from app.config import settings
from app.utils.response import CODE_GITHUB_ERROR, BusinessError

logger = logging.getLogger(__name__)

# README 内容长度下限（字符），用于判断「README 是否完整」
_README_MIN_LENGTH = 400


@dataclass
class GithubRepo:
    """精简后的 GitHub 仓库信息。"""

    full_name: str
    name: str
    url: str
    description: str
    stars: int
    language: str | None
    topics: list[str] = field(default_factory=list)
    updated_at: str = ""
    readme_length: int = 0
    homepage: str | None = None

    def to_prompt_line(self, index: int) -> str:
        """格式化为 Prompt 中的一行候选描述。"""
        desc = (self.description or "无描述").strip()
        topics = "、".join(self.topics[:6]) if self.topics else "无"
        return (
            f"[{index}] 仓库：{self.full_name}\n"
            f"    项目描述：{desc}\n"
            f"    主要语言：{self.language or '未标注'} | Star 数：{self.stars}\n"
            f"    技术标签：{topics}\n"
            f"    最近更新：{self.updated_at[:10]}\n"
            f"    仓库地址：{self.url}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "stars": self.stars,
            "language": self.language,
            "topics": self.topics,
            "updated_at": self.updated_at,
            "readme_length": self.readme_length,
            "homepage": self.homepage,
        }


class GithubService:
    """GitHub 检索封装（全异步，带并发 README 校验）。"""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ProjectMentor/1.0",
        }
        # 配置了 Token 时启用鉴权，速率限制从 10 次/分 提升到 30 次/分（搜索接口）
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.GITHUB_API_BASE,
                headers=self._headers(),
                timeout=20.0,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------

    def _build_query(self, keywords: str, language: str | None) -> str:
        """拼装 GitHub 搜索限定条件。"""
        # 近一年内有更新
        since = (date.today() - timedelta(days=365)).isoformat()
        parts = [keywords, f"stars:>{settings.GITHUB_MIN_STARS}", f"pushed:>{since}"]
        if language:
            parts.append(f'language:"{language}"')
        # 排除教程/面试题/awesome 合集类仓库，它们不是「可实战的项目」
        parts.append("NOT awesome")
        parts.append("NOT tutorial")
        parts.append("NOT interview")
        return " ".join(part for part in parts if part)

    async def search(
        self,
        keywords: str,
        language: str | None = None,
        limit: int | None = None,
    ) -> list[GithubRepo]:
        """检索候选仓库（已完成 README 校验与排序）。

        :param keywords: 英文技术关键词，如 "react frontend"
        :param language: 主要语言限定，可为空
        :param limit: 返回条数上限，默认取配置的候选数
        """
        limit = limit or settings.GITHUB_CANDIDATE_LIMIT
        client = await self._get_client()

        params = {
            "q": self._build_query(keywords, language),
            "sort": "stars",
            "order": "desc",
            "per_page": min(max(limit * 2, 10), 50),  # 多取一些，README 校验后再截断
        }

        try:
            response = await client.get("/search/repositories", params=params)
        except httpx.HTTPError as exc:
            logger.exception("GitHub 搜索请求失败")
            raise BusinessError(f"GitHub 接口访问失败：{exc}", CODE_GITHUB_ERROR) from exc

        if response.status_code == 403:
            raise BusinessError(
                "GitHub 接口触发速率限制，请稍后重试或在 .env 中配置 GITHUB_TOKEN",
                CODE_GITHUB_ERROR,
            )
        if response.status_code >= 400:
            raise BusinessError(
                f"GitHub 搜索失败（HTTP {response.status_code}）", CODE_GITHUB_ERROR
            )

        payload = response.json()
        items = payload.get("items", []) or []
        repos = [self._parse_repo(item) for item in items]

        # 并发校验 README 完整性
        readme_lengths = await asyncio.gather(
            *(self._fetch_readme_length(repo.full_name) for repo in repos),
            return_exceptions=True,
        )
        qualified: list[GithubRepo] = []
        for repo, length in zip(repos, readme_lengths, strict=False):
            repo.readme_length = length if isinstance(length, int) else 0
            # README 缺失或过于简陋的仓库不作为实战候选
            if repo.readme_length >= _README_MIN_LENGTH:
                qualified.append(repo)

        qualified.sort(key=lambda repo: repo.stars, reverse=True)
        return qualified[:limit]

    @staticmethod
    def _parse_repo(item: dict[str, Any]) -> GithubRepo:
        """把 GitHub 原始响应转换为内部结构。"""
        return GithubRepo(
            full_name=item.get("full_name", ""),
            name=item.get("name", ""),
            url=item.get("html_url", ""),
            description=item.get("description") or "",
            stars=item.get("stargazers_count", 0) or 0,
            language=item.get("language"),
            topics=item.get("topics") or [],
            updated_at=item.get("pushed_at") or item.get("updated_at") or "",
            homepage=item.get("homepage"),
        )

    async def _fetch_readme_length(self, full_name: str) -> int:
        """获取 README 正文长度，用于判断文档是否完整；失败按 0 处理。"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"/repos/{full_name}/readme",
                headers={"Accept": "application/vnd.github.raw"},
            )
            if response.status_code == 200:
                return len(response.text or "")
        except httpx.HTTPError:
            logger.debug("获取 README 失败：%s", full_name)
        return 0

    def render_candidates(self, repos: list[GithubRepo]) -> str:
        """把候选仓库列表渲染为 Prompt 片段。"""
        if not repos:
            return "（无候选项目）"
        return "\n\n".join(repo.to_prompt_line(index) for index, repo in enumerate(repos))


_github_service: GithubService | None = None


def get_github_service() -> GithubService:
    """获取 GitHub 服务单例。"""
    global _github_service
    if _github_service is None:
        _github_service = GithubService()
    return _github_service
