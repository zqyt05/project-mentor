"""项目匹配路由逻辑测试。

重点覆盖「技术类方向下 GitHub 优质项目不足时，用 AI 定制项目补齐差额」这一策略：
- 完全够数 → 全部来自 GitHub，不额外调用定制生成
- 部分不足 → 保留已找到的 GitHub 项目，只补齐差额
- 一个都没有 → 全部由 AI 定制

测试通过替换 `project_service` 模块内的三个协作者，完全离线运行，
不触发任何 LLM 或 GitHub 请求。
"""

import asyncio

import pytest

from app.models import ProjectSource
from app.schemas.project import ProjectCandidate
from app.services import project_service as ps


def make_candidate(name: str, source: str) -> ProjectCandidate:
    """构造一个最小可用的候选项目。"""
    return ProjectCandidate(
        name=name,
        source=source,  # type: ignore[arg-type]
        difficulty="入门",
        summary=f"{name} 的简介",
        deliverables=["产出物 A"],
    )


def patch_collaborators(
    monkeypatch: pytest.MonkeyPatch,
    github_candidates: list[ProjectCandidate],
    recorded: dict,
) -> None:
    """把领域判断 / GitHub 检索 / 定制生成替换为可控的假实现。"""

    async def fake_classify(_domain: str) -> dict:
        return {
            "category": "technical",
            "reason": "属于编程技术方向",
            "search_keywords": "react",
            "language": "JavaScript",
            "custom_hint": "",
        }

    async def fake_github(*_args, **_kwargs) -> list[ProjectCandidate]:
        return list(github_candidates)

    async def fake_custom(_domain: str, _difficulty: str, count: int = 3):
        recorded["count"] = count
        recorded["called"] = True
        return [make_candidate(f"定制项目{i + 1}", ProjectSource.CUSTOM) for i in range(count)]

    monkeypatch.setattr(ps, "classify_domain", fake_classify)
    monkeypatch.setattr(ps, "match_github_projects", fake_github)
    monkeypatch.setattr(ps, "generate_custom_projects", fake_custom)


class TestGithubShortageTopUp:
    """GitHub 优质项目不足 3 个时，用定制项目补齐而不是整体降级。"""

    def test_enough_github_projects_skips_custom(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded: dict = {}
        patch_collaborators(
            monkeypatch,
            [make_candidate(f"gh{i}", ProjectSource.GITHUB) for i in range(4)],
            recorded,
        )

        result = asyncio.run(ps.match_projects("React 前端入门", "入门"))

        assert result.path == ProjectSource.GITHUB
        assert len(result.projects) == 4
        assert all(p.source == ProjectSource.GITHUB for p in result.projects)
        assert "called" not in recorded, "项目数足够时不应调用定制生成"

    def test_two_github_projects_are_topped_up_with_one_custom(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """核心用例：只有 2 个开源项目时，保留它们并补 1 个定制项目。"""
        recorded: dict = {}
        patch_collaborators(
            monkeypatch,
            [make_candidate("gh1", ProjectSource.GITHUB), make_candidate("gh2", ProjectSource.GITHUB)],
            recorded,
        )

        result = asyncio.run(ps.match_projects("React 前端入门", "入门"))

        assert len(result.projects) == 3, "总数应补齐到 3 个"
        github_count = sum(1 for p in result.projects if p.source == ProjectSource.GITHUB)
        custom_count = sum(1 for p in result.projects if p.source == ProjectSource.CUSTOM)
        assert (github_count, custom_count) == (2, 1)
        assert recorded["count"] == 1, "只应补齐差额 1 个"
        # GitHub 项目排在前面，保持「优先复用开源项目」的产品意图
        assert result.projects[0].source == ProjectSource.GITHUB
        assert result.path == ProjectSource.GITHUB
        assert "补齐" in result.route_reason

    def test_one_github_project_is_topped_up_with_two_custom(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded: dict = {}
        patch_collaborators(
            monkeypatch, [make_candidate("gh1", ProjectSource.GITHUB)], recorded
        )

        result = asyncio.run(ps.match_projects("React 前端入门", "入门"))

        assert len(result.projects) == 3
        assert recorded["count"] == 2
        assert result.projects[0].source == ProjectSource.GITHUB

    def test_no_github_project_falls_back_entirely_to_custom(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded: dict = {}
        patch_collaborators(monkeypatch, [], recorded)

        result = asyncio.run(ps.match_projects("React 前端入门", "入门"))

        assert result.path == ProjectSource.CUSTOM
        assert len(result.projects) == 3
        assert all(p.source == ProjectSource.CUSTOM for p in result.projects)
        assert recorded["count"] == 3


class TestGithubSearchThreshold:
    """检索结果不再因为「少于 3 个」被直接丢弃。"""

    def test_match_github_projects_returns_partial_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """只找到 2 个时应返回这 2 个，而不是空列表。"""
        from app.services.github_service import GithubRepo

        repos = [
            GithubRepo(
                full_name=f"owner/repo{i}",
                name=f"repo{i}",
                url=f"https://github.com/owner/repo{i}",
                description="描述",
                stars=1000 + i,
                language="JavaScript",
                readme_length=2000,
            )
            for i in range(2)
        ]

        class FakeGithub:
            async def search(self, *_args, **_kwargs):
                return repos

            def render_candidates(self, items):
                return "\n".join(r.full_name for r in items)

        class FakeLlm:
            async def acomplete_json(self, **_kwargs):
                return {
                    "projects": [
                        {"index": 0, "fit": 90, "summary": "s", "deliverables": ["d"]},
                        {"index": 1, "fit": 80, "summary": "s", "deliverables": ["d"]},
                    ]
                }

        monkeypatch.setattr(ps, "get_github_service", lambda: FakeGithub())
        monkeypatch.setattr(ps, "get_llm_service", lambda: FakeLlm())

        candidates = asyncio.run(
            ps.match_github_projects("React 前端入门", "入门", "react", "JavaScript")
        )

        assert len(candidates) == 2
        assert all(c.source == ProjectSource.GITHUB for c in candidates)
