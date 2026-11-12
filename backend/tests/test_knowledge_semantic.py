"""知识库的**真实向量检索**用例。

与 test_knowledge.py 分开的原因：
后者用 autouse 夹具把所有向量化替换成「不可用」，以便在离线环境（CI）
快速、确定地测试关键词降级路径。而语义检索这条主路径也必须被真正
执行过一次 —— 否则「向量检索坏了」在 CI 里永远发现不了
（与每日配额那次「测试全绿但接口 500」的教训同源）。

本文件的用例在模型不可用时自动 skip，不阻塞 CI；本地有模型缓存时会真实运行。
"""

import os

import pytest
from sqlalchemy.orm import Session

from app.models import Project
from app.services import knowledge_service as ks
from tests.test_knowledge import SAMPLE


def _semantic_available() -> bool:
    """本机是否具备真实向量检索条件。

    CI 环境（GitHub Actions 会自动设置 CI=true）无法下载约 91MB 模型，
    且下载失败要重试约 60 秒 —— 直接跳过，避免拖慢流水线。
    本地有模型缓存时会真实运行，`uv run pytest` 即可验证语义检索。
    """
    if os.environ.get("CI"):
        return False
    return ks.embedding_available()


@pytest.fixture()
def project(db: Session) -> Project:
    item = Project(name="语义检索项目", domain="财务分析", difficulty="入门")
    db.add(item)
    db.commit()
    return item


class TestRealSemanticRetrieval:
    """需要真实向量模型（约 91MB，首次使用会从镜像下载）。"""

    def test_model_available_or_skip(self, project: Project, db: Session) -> None:
        if not _semantic_available():
            pytest.skip("向量模型不可用（CI 或离线/无缓存），跳过语义检索用例")

        document = ks.add_document(db, project.id, "财务笔记.txt", SAMPLE.encode())
        assert document.embedded is True, "向量化应成功"
        assert document.chunk_count >= 2

    def test_paraphrase_question_hits_right_chunk(self, project: Project, db: Session) -> None:
        """用「字面不重合但意思相同」的问题，验证确实是语义检索在起作用。"""
        if not _semantic_available():
            pytest.skip("向量模型不可用（CI 或离线/无缓存），跳过语义检索用例")

        ks.add_document(db, project.id, "财务笔记.txt", SAMPLE.encode())

        # "存货变现速度快慢怎么衡量" 与原文「存货周转率…反映存货变现的速度」
        # 字面重叠极少（只共享"存货""变现""速度"），语音检索能命中说明向量有效
        results = ks.retrieve(db, project.id, "用什么指标衡量存货变现快慢")
        assert results, "语义检索应命中存货相关片段"
        assert any("周转" in item.content or "365" in item.content for item in results)

    def test_unrelated_question_returns_nothing(self, project: Project, db: Session) -> None:
        """无关问题即使走向量检索也不应硬塞内容。"""
        if not _semantic_available():
            pytest.skip("向量模型不可用（CI 或离线/无缓存），跳过语义检索用例")

        ks.add_document(db, project.id, "财务笔记.txt", SAMPLE.encode())
        assert ks.retrieve(db, project.id, "今天天气怎么样适合爬山吗") == []
