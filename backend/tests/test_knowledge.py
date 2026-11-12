"""知识库（RAG）单元测试。

全部离线：默认把向量化替换为「不可用」，走关键词检索分支 ——
这与 CI 环境一致（无法下载 91MB 模型），也让断言完全确定。
真正加载模型的用例放在最后，模型不可用时自动跳过。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Project
from app.services import knowledge_service as ks


@pytest.fixture(autouse=True)
def _offline_embedding(monkeypatch: pytest.MonkeyPatch):
    """默认禁用向量化，强制走关键词分支：离线、确定、快速。"""
    monkeypatch.setattr(ks, "embed_texts", lambda texts: None)
    monkeypatch.setattr(ks, "embedding_available", lambda: False)


def _make_project(db: Session, name: str = "测试项目", owner_id: str | None = None) -> Project:
    project = Project(name=name, domain="财务分析", difficulty="入门", owner_id=owner_id)
    db.add(project)
    db.commit()
    return project


SAMPLE = """第一章 存货管理

存货周转率是衡量企业存货管理效率的核心指标。它的计算公式是：存货周转率 = 销货成本 / 平均存货余额。
平均存货余额 =（期初存货 + 期末存货）/ 2。这个指标反映存货变现的速度，周转率越高说明资金使用效率越高。
但也不是越高越好，过高可能是备货不足，会导致缺货损失订单。

与它相关的还有存货周转天数：存货周转天数 = 365 / 存货周转率。周转天数越短，说明从进货到卖出越快。
常见误区是只看周转率不看毛利率——如果为了加快周转而大幅降价，周转率上去了但利润被吃掉了。

第二章 现金流量表

现金流量表反映企业一段时间内现金的流入流出，分为经营活动、投资活动、筹资活动三类。
经营性现金流为正，说明主营业务能够自己造血，这是企业健康的重要标志。

很多企业利润表很好看却倒闭了，原因就是经营性现金流为负：货卖出去了但钱没收回来，应收账款堆积。
所以要特别关注净利润与经营性现金流的差额，这个差额长期为负就要警惕。

第三章 三张报表的勾稽关系

资产负债表是时点快照，利润表和现金流量表是时期记录。三张表的勾稽关系体现在几个方面：
利润表的净利润会进入资产负债表的未分配利润；现金流量表的期末现金余额要等于资产负债表的货币资金。
如果勾稽不上，说明账务处理有问题，通常是漏记了某些业务，或者把不同性质的收支混在一起。
实务中这是最常见的对账线索，也是新人最容易忽略的检查点。"""


class TestChunking:
    """分块：不能丢内容，块大小要受控。"""

    def test_short_text_is_single_chunk(self) -> None:
        assert len(ks.chunk_text("很短的一段话。")) == 1

    def test_empty_text(self) -> None:
        assert ks.chunk_text("   ") == []

    def test_long_text_splits(self) -> None:
        text = "这是一句话。" * 300  # 1800 字
        chunks = ks.chunk_text(text)
        assert len(chunks) > 1
        # 除最后一块外都不应超出上限太多（含重叠）
        for chunk in chunks[:-1]:
            assert len(chunk) <= ks.CHUNK_SIZE + ks.CHUNK_OVERLAP + 10

    def test_no_content_loss(self) -> None:
        """所有段落都必须能在某个块里找到 —— 分块丢掉内容是最危险的 bug。"""
        chunks = ks.chunk_text(SAMPLE)
        for paragraph in [p.strip() for p in SAMPLE.split("\n\n") if p.strip()]:
            head = paragraph[:25]
            assert any(head in chunk for chunk in chunks), f"丢失段落：{head}"

    def test_keywords_preserved(self) -> None:
        joined = "".join(ks.chunk_text(SAMPLE))
        for keyword in ["365", "应收账款", "未分配利润", "勾稽"]:
            assert keyword in joined


class TestParsing:
    """文件解析与类型校验。"""

    def test_txt(self) -> None:
        text, file_type = ks.parse_document("笔记.txt", "内容".encode())
        assert file_type == "txt"
        assert text == "内容"

    def test_markdown(self) -> None:
        text, file_type = ks.parse_document("笔记.md", "# 标题\n正文".encode())
        assert file_type == "md"
        assert "标题" in text

    def test_unsupported_type_rejected(self) -> None:
        from app.utils.response import BusinessError

        with pytest.raises(BusinessError, match="不支持的文件类型"):
            ks.parse_document("图片.png", b"fake")

    def test_empty_file_rejected(self) -> None:
        from app.utils.response import BusinessError

        with pytest.raises(BusinessError, match="内容为空"):
            ks.parse_document("空.txt", b"")

    def test_oversized_rejected(self) -> None:
        from app.utils.response import BusinessError

        with pytest.raises(BusinessError, match="文件过大"):
            ks.parse_document("大.txt", b"x" * (ks.MAX_FILE_BYTES + 1))

    def test_docx(self) -> None:
        """真实构造一个 docx 验证解析（含表格）。"""
        import io

        from docx import Document

        document = Document()
        document.add_paragraph("存货周转率衡量变现速度")
        table = document.add_table(rows=1, cols=2)
        table.rows[0].cells[0].text = "存货周转天数"
        table.rows[0].cells[1].text = "365 / 周转率"
        buffer = io.BytesIO()
        document.save(buffer)

        text, file_type = ks.parse_document("笔记.docx", buffer.getvalue())
        assert file_type == "docx"
        assert "存货周转率" in text
        assert "365 / 周转率" in text  # 表格内容也要抽出来


class TestKeywordFallback:
    """向量不可用时，关键词检索必须仍然可用。"""

    def test_keyword_score_matches_related(self) -> None:
        score = ks._keyword_score("存货周转", "存货周转率 = 销货成本 / 平均存货余额")
        assert score > 0

    def test_keyword_score_rejects_unrelated(self) -> None:
        assert ks._keyword_score("存货周转", "React 的 useEffect 依赖数组") == 0


class TestAddAndRetrieve:
    """落库与检索。"""

    def test_add_document_creates_chunks(self, db: Session) -> None:
        project = _make_project(db)
        document = ks.add_document(db, project.id, "笔记.txt", SAMPLE.encode())

        assert document.chunk_count > 1
        assert document.char_count > 0
        # 向量化被禁用 → 应标记为未向量化，供界面提示降级
        assert document.embedded is False

    def test_retrieve_finds_relevant_chunk(self, db: Session) -> None:
        project = _make_project(db)
        ks.add_document(db, project.id, "笔记.txt", SAMPLE.encode())

        results = ks.retrieve(db, project.id, "周转天数怎么算")
        assert results, "应当检索到内容"
        assert any("365" in r.content for r in results)
        assert results[0].filename == "笔记.txt"

    def test_retrieve_returns_empty_for_unrelated(self, db: Session) -> None:
        """无关问题不应硬塞不相关内容进上下文。"""
        project = _make_project(db)
        ks.add_document(db, project.id, "笔记.txt", SAMPLE.encode())
        assert ks.retrieve(db, project.id, "今天天气怎么样适合爬山吗") == []

    def test_retrieve_scoped_to_project(self, db: Session) -> None:
        """A 项目的资料不能出现在 B 项目的检索结果里。"""
        project_a = _make_project(db, "项目A")
        project_b = _make_project(db, "项目B")
        ks.add_document(db, project_a.id, "a.txt", SAMPLE.encode())

        assert ks.retrieve(db, project_a.id, "周转天数") != []
        assert ks.retrieve(db, project_b.id, "周转天数") == []

    def test_context_has_numbered_sources(self, db: Session) -> None:
        project = _make_project(db)
        ks.add_document(db, project.id, "财务笔记.txt", SAMPLE.encode())
        context = ks.build_retrieval_context(ks.retrieve(db, project.id, "周转天数"))

        assert "[资料1]" in context
        assert "财务笔记.txt" in context

    def test_empty_context_when_no_hits(self) -> None:
        assert ks.build_retrieval_context([]) == ""


class TestDocumentsManagement:
    """资料的增删查。"""

    def test_list_and_delete(self, db: Session) -> None:
        project = _make_project(db)
        first = ks.add_document(db, project.id, "一.txt", SAMPLE.encode())
        ks.add_document(db, project.id, "二.txt", SAMPLE.encode())

        assert len(ks.list_documents(db, project.id)) == 2
        ks.delete_document(db, project.id, first.id)
        remaining = ks.list_documents(db, project.id)
        assert len(remaining) == 1
        assert remaining[0].filename == "二.txt"

    def test_delete_removes_chunks(self, db: Session) -> None:
        from app.models import KnowledgeChunk

        project = _make_project(db)
        document = ks.add_document(db, project.id, "笔记.txt", SAMPLE.encode())
        assert db.query(KnowledgeChunk).filter_by(document_id=document.id).count() > 0

        ks.delete_document(db, project.id, document.id)
        assert db.query(KnowledgeChunk).filter_by(document_id=document.id).count() == 0

    def test_delete_other_projects_document_rejected(self, db: Session) -> None:
        from app.utils.response import BusinessError

        project_a = _make_project(db, "A")
        project_b = _make_project(db, "B")
        document = ks.add_document(db, project_a.id, "笔记.txt", SAMPLE.encode())

        with pytest.raises(BusinessError, match="资料不存在"):
            ks.delete_document(db, project_b.id, document.id)


class TestApi:
    """HTTP 接口与归属隔离。"""

    def test_upload_and_list(self, client: TestClient, db: Session) -> None:
        project = _make_project(db)
        response = client.post(
            f"/api/knowledge/{project.id}/upload",
            files={"file": ("笔记.txt", SAMPLE.encode(), "text/plain")},
        )
        body = response.json()
        assert body["code"] == 0
        assert body["data"]["chunk_count"] > 1

        listing = client.get(f"/api/knowledge/{project.id}").json()["data"]
        assert len(listing["documents"]) == 1
        assert listing["semantic_search"] is False  # 测试环境禁用了向量
        assert "docx" in listing["supported_types"]

    def test_search_endpoint(self, client: TestClient, db: Session) -> None:
        project = _make_project(db)
        client.post(
            f"/api/knowledge/{project.id}/upload",
            files={"file": ("笔记.txt", SAMPLE.encode(), "text/plain")},
        )
        body = client.get(
            f"/api/knowledge/{project.id}/search", params={"q": "周转天数"}
        ).json()
        assert body["data"]["sources"]
        assert "365" in body["data"]["sources"][0]["content"]

    def test_upload_rejects_unsupported_type(self, client: TestClient, db: Session) -> None:
        project = _make_project(db)
        body = client.post(
            f"/api/knowledge/{project.id}/upload",
            files={"file": ("图.png", b"fake", "image/png")},
        ).json()
        assert body["code"] == 400
        assert "不支持" in body["message"]

    def test_other_visitor_cannot_access(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        """他人项目的知识库必须不可达（返回 404，不泄露存在性）。"""
        other = _make_project(db, "别人的项目", owner_id="someone-else")
        ks.add_document(db, other.id, "机密.txt", SAMPLE.encode())

        client.post("/api/auth/login", json={"password": enable_gate})
        body = client.get(f"/api/knowledge/{other.id}").json()
        assert body["code"] == 404

        # 也检索不到别人的内容
        body = client.post(
            f"/api/knowledge/{other.id}/upload",
            files={"file": ("偷.txt", SAMPLE.encode(), "text/plain")},
        ).json()
        assert body["code"] == 404

    def test_own_project_accessible(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        """拦截不能误伤：访客必须能用自己的知识库。"""
        from app.services import auth_service

        client.post("/api/auth/login", json={"password": enable_gate})
        visitor_id = auth_service.parse_token(client.cookies.get(auth_service.VISITOR_COOKIE))
        own = _make_project(db, "我的项目", owner_id=visitor_id)

        body = client.post(
            f"/api/knowledge/{own.id}/upload",
            files={"file": ("我的笔记.txt", SAMPLE.encode(), "text/plain")},
        ).json()
        assert body["code"] == 0
        assert client.get(f"/api/knowledge/{own.id}").json()["data"]["documents"]
